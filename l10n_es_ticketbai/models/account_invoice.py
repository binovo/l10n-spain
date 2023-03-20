# Copyright 2021 Binovo IT Human Project SL
# Copyright 2021 Landoo Sistemas de Informacion SL
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import datetime
import re
from odoo import models, fields, exceptions, _, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.l10n_es_ticketbai_api.models.ticketbai_invoice import RefundCode, \
    RefundType, SiNoType, TicketBaiInvoiceState
from odoo.addons.l10n_es_ticketbai_api.ticketbai.xml_schema import TicketBaiSchema
from odoo.tools.float_utils import float_round
from odoo.tools import float_is_zero


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    tbai_enabled = fields.Boolean(related='company_id.tbai_enabled', readonly=True)
    tbai_invoice_id = fields.Many2one(
        comodel_name='tbai.invoice', string='TicketBAI Invoice',
        copy=False)
    tbai_invoice_ids = fields.One2many(
        comodel_name='tbai.invoice', inverse_name='invoice_id',
        string='TicketBAI Invoices')
    tbai_cancellation_id = fields.Many2one(
        comodel_name='tbai.invoice',
        string='TicketBAI Cancellation', copy=False)
    tbai_cancellation_ids = fields.One2many(
        comodel_name='tbai.invoice', inverse_name='cancelled_invoice_id',
        string='TicketBAI Cancellations')
    tbai_response_ids = fields.Many2many(
        comodel_name='tbai.response', compute='_compute_tbai_response_ids',
        string='Responses')
    tbai_expedition_date = fields.Char(
        string="Expedition date",
        related="tbai_invoice_id.expedition_date",
        readonly=True,
        help="TicketBai expedition date format: %dd-%mm-%yyyy",
    )
    tbai_description_operation = fields.Text(
        'Operation Description', default="/", copy=False)
    tbai_substitute_simplified_invoice = fields.Boolean(
        'Substitute Simplified Invoice', copy=False)
    tbai_refund_key = fields.Selection(selection=[
        (RefundCode.R1.value, 'Art. 80.1, 80.2, 80.6 and rights founded error'),
        (RefundCode.R2.value, 'Art. 80.3'),
        (RefundCode.R3.value, 'Art. 80.4'),
        (RefundCode.R4.value, 'Art. 80 - other')
    ],
        help="BOE-A-1992-28740. Ley 37/1992, de 28 de diciembre, del Impuesto sobre el "
             "Valor Añadido. Artículo 80. Modificación de la base imponible.",
        copy=False)
    tbai_refund_type = fields.Selection(selection=[
        (RefundType.substitution.value, 'By substitution'),
        (RefundType.differences.value, 'By differences')
    ], copy=False)
    tbai_vat_regime_key = fields.Many2one(
        comodel_name='tbai.vat.regime.key', string='VAT Regime Key', copy=True)
    tbai_vat_regime_key2 = fields.Many2one(
        comodel_name='tbai.vat.regime.key', string='VAT Regime 2nd Key', copy=True)
    tbai_vat_regime_key3 = fields.Many2one(
        comodel_name='tbai.vat.regime.key', string='VAT Regime 3rd Key', copy=True)
    tbai_refund_origin_ids = fields.One2many(
        comodel_name='tbai.invoice.refund.origin',
        inverse_name='account_refund_invoice_id',
        string='TicketBAI Refund Origin References')
    has_surcharge_lines = fields.Boolean(compute='_compute_surcharge_lines')
    error_surcharge_lines = fields.Boolean(compute='_compute_surcharge_lines')

    @api.multi
    @api.constrains('state')
    def _check_cancel_number_invoice(self):
        for record in self:
            if record.type in ('out_invoice', 'out_refund') and \
                    record.tbai_enabled and 'draft' == record.state and record.number:
                raise exceptions.ValidationError(_(
                    "Invoice %s. You cannot change to draft a numbered invoice!"
                ) % record.number)

    @api.multi
    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise exceptions.UserError(_(
                    'You cannot delete an invoice which is not draft. '
                    'You should create a credit note instead.'))
        return super().unlink()

    @api.model
    def create(self, vals):
        if vals.get('company_id', False):
            company = self.env['res.company'].browse(vals['company_id'])
        else:
            company = self.env.user.company_id
        if company.tbai_enabled:
            filter_refund = self._context.get('filter_refund', False) \
                or self._context.get('type', False) == 'out_refund'
            invoice_type = vals.get('type', False) \
                or self._context.get('type', False)
            if filter_refund and invoice_type:
                if 'out_refund' == invoice_type:
                    if not vals.get('tbai_refund_type', False):
                        vals['tbai_refund_type'] = RefundType.differences.value
                    if not vals.get('tbai_refund_key', False):
                        vals['tbai_refund_key'] = RefundCode.R1.value
            if vals.get('fiscal_position_id', False) and\
               not vals.get('tbai_vat_regime_key', False):
                fiscal_position =\
                    self.env['account.fiscal.position'].browse(
                        vals['fiscal_position_id'])
                vals['tbai_vat_regime_key'] =\
                    fiscal_position.tbai_vat_regime_key.id
                vals['tbai_vat_regime_key2'] =\
                    fiscal_position.tbai_vat_regime_key2.id
                vals['tbai_vat_regime_key3'] =\
                    fiscal_position.tbai_vat_regime_key3.id
        return super().create(vals)

    def is_surcharge_or_simplified_regime_key(self):
        self.ensure_one()
        return True if self.tbai_vat_regime_key.id in [
            self.env.ref("l10n_es_ticketbai.tbai_vat_regime_51").id,
            self.env.ref("l10n_es_ticketbai.tbai_vat_regime_52").id
        ] else False

    @api.depends('invoice_line_ids')
    def _compute_surcharge_lines(self):
        for record in self:
            surcharge_line_ids = record.invoice_line_ids.filtered(
                lambda l: l.product_id.has_equivalence_surcharge is True)
            no_surcharge_line_ids = record.invoice_line_ids.filtered(
                lambda l: l.product_id.has_equivalence_surcharge is False)
            record.has_surcharge_lines = True if surcharge_line_ids else False
            if (record.is_surcharge_or_simplified_regime_key()
                    and surcharge_line_ids
                    and no_surcharge_line_ids):
                record.error_surcharge_lines = True
            else:
                record.error_surcharge_lines = False

    @api.depends(
        'tbai_invoice_ids', 'tbai_invoice_ids.state',
        'tbai_cancellation_ids', 'tbai_cancellation_ids.state'
    )
    def _compute_tbai_response_ids(self):
        for record in self:
            response_ids = record.tbai_invoice_ids.mapped('tbai_response_ids').ids
            response_ids += record.tbai_cancellation_ids.mapped('tbai_response_ids').ids
            record.tbai_response_ids = [(6, 0, response_ids)]

    @api.onchange('fiscal_position_id')
    def onchange_fiscal_position_id_tbai_vat_regime_key(self):
        if self.company_id.tbai_vat_regime.id in [
            self.env.ref("l10n_es_ticketbai.tbai_vat_regime_51").id,
            self.env.ref("l10n_es_ticketbai.tbai_vat_regime_52").id
        ]:
            self.tbai_vat_regime_key = self.company_id.tbai_vat_regime.id
        elif self.fiscal_position_id:
            self.tbai_vat_regime_key =\
                self.fiscal_position_id.tbai_vat_regime_key.id
            self.tbai_vat_regime_key2 =\
                self.fiscal_position_id.tbai_vat_regime_key2.id
            self.tbai_vat_regime_key3 =\
                self.fiscal_position_id.tbai_vat_regime_key3.id

    @api.onchange('invoice_line_ids')
    def onchange_invoice_line_ids_tbai_vat_regime_key(self):
        if self.company_id.tbai_vat_regime.id in [
            self.env.ref("l10n_es_ticketbai.tbai_vat_regime_51").id,
            self.env.ref("l10n_es_ticketbai.tbai_vat_regime_52").id
        ]:
            self.tbai_vat_regime_key =\
                self.company_id.tbai_vat_regime.id if self.has_surcharge_lines or\
                len(self.invoice_line_ids) == 0 else \
                self.env.ref("l10n_es_ticketbai.tbai_vat_regime_01").id

    @api.onchange('tbai_refund_type')
    def onchange_tbai_refund_type(self):
        if self.tbai_refund_type:
            if ('out_invoice' != self.type or
                    ('out_invoice' == self.type and not
                        self.tbai_substitute_simplified_invoice)) and \
                    RefundType.substitution.value == self.tbai_refund_type:
                self.tbai_refund_type = False
                return {
                    'warning': {
                        'title': _("Warning"),
                        'message': _(
                            "TicketBAI refund by substitution is not supported.")
                    }
                }
            elif 'out_refund' != self.type and \
                    RefundType.differences.value == self.tbai_refund_type:
                self.tbai_refund_type = False
                return {
                    'warning': {
                        'title': _("Warning"),
                        'message': _(
                            "TicketBAI refund by differences only available for "
                            "Customer Credit Notes.")
                    }
                }

    @api.onchange('refund_invoice_id')
    def onchange_tbai_refund_invoice_id(self):
        if self.refund_invoice_id:
            if not self.tbai_refund_type:
                self.tbai_refund_type = RefundType.differences.value
            if not self.tbai_refund_key:
                self.tbai_refund_key = RefundCode.R1.value

    def tbai_prepare_invoice_values(self):

        def tbai_prepare_refund_values():
            refunded_inv = self.refund_invoice_id
            if refunded_inv:
                refund_datetime = refunded_inv.date or refunded_inv.invoice_date
                refund_expedition_date = (
                    refunded_inv.tbai_expedition_date
                    or refunded_inv.tbai_get_value_fecha_expedicion_factura(
                        invoice_datetime=refund_datetime
                    )
                )
                vals.update({
                    'is_invoice_refund': True,
                    'refund_code': self.tbai_refund_key,
                    'refund_type': self.tbai_refund_type,
                    'tbai_invoice_refund_ids': [(0, 0, {
                        'number_prefix': refunded_inv.tbai_get_value_serie_factura(),
                        'number': refunded_inv.tbai_get_value_num_factura(),
                        'expedition_date': refund_expedition_date
                    })]
                })
            else:
                if self.tbai_refund_origin_ids:
                    refund_id_dicts = []
                    for refund_origin_id in self.tbai_refund_origin_ids:
                        expedition_date = fields.Date.from_string(
                            refund_origin_id.expedition_date).strftime("%d-%m-%Y")
                        refund_id_dicts.append(
                            (0, 0, {
                                'number_prefix': refund_origin_id.number_prefix,
                                'number': refund_origin_id.number,
                                'expedition_date': expedition_date
                            }))
                    vals.update({
                        'is_invoice_refund': True,
                        'refund_code': self.tbai_refund_key,
                        'refund_type': self.tbai_refund_type,
                        'tbai_invoice_refund_ids': refund_id_dicts
                    })

        self.ensure_one()
        expedition_datetime = fields.Datetime.now()
        expedition_date = self.tbai_get_value_fecha_expedicion_factura(
            invoice_datetime=expedition_datetime
        )
        expedition_hour = self.tbai_get_value_hora_expedicion_factura(
            invoice_datetime=expedition_datetime
        )
        vals = {
            'invoice_id': self.id,
            'schema': TicketBaiSchema.TicketBai.value,
            'name': self._get_printed_report_name(),
            'company_id': self.company_id.id,
            'number_prefix': self.tbai_get_value_serie_factura(),
            'number': self.tbai_get_value_num_factura(),
            'expedition_date': expedition_date,
            'expedition_hour': expedition_hour,
            'substitutes_simplified_invoice':
                self.tbai_get_value_factura_emitida_sustitucion_simplificada(),
            'description': self.tbai_description_operation,
            'amount_total': "%.2f" % self.amount_total_company_signed,
            'vat_regime_key': self.tbai_vat_regime_key.code,
            'vat_regime_key2': self.tbai_vat_regime_key2.code,
            'vat_regime_key3': self.tbai_vat_regime_key3.code
        }
        retencion_soportada = self.tbai_get_value_retencion_soportada()
        if retencion_soportada:
            vals['tax_retention_amount_total'] = retencion_soportada
        if self.tbai_is_invoice_refund() and \
                RefundType.differences.value == self.tbai_refund_type:
            tbai_prepare_refund_values()
        operation_date = self.tbai_get_value_fecha_operacion()
        if operation_date and operation_date != expedition_date:
            vals['operation_date'] = operation_date
        gipuzkoa_tax_agency = self.env.ref(
            "l10n_es_ticketbai_api.tbai_tax_agency_gipuzkoa")
        araba_tax_agency = self.env.ref(
            "l10n_es_ticketbai_api.tbai_tax_agency_araba")
        tax_agency = self.company_id.tbai_tax_agency_id
        if tax_agency in (gipuzkoa_tax_agency, araba_tax_agency):
            lines = []
            for line in self.invoice_line_ids:
                description_line = line.name[:250]
                if self.company_id.tbai_protected_data \
                   and self.company_id.tbai_protected_data_txt:
                    description_line = self.company_id.tbai_protected_data_txt[:250]
                lines.append((0, 0, {
                    'description': description_line,
                    'quantity': line.tbai_get_value_cantidad(),
                    'price_unit': line.tbai_get_value_price_unit(),
                    'discount_amount': line.tbai_get_value_descuento(),
                    'amount_total': line.tbai_get_value_importe_total()
                }))
            vals['tbai_invoice_line_ids'] = lines
        taxes = []
        tbai_maps = self.env["tbai.tax.map"].search(
            [('code', 'in', ("RE", "IRPF"))]
        )
        exclude_taxes = self.env['l10n.es.aeat.report'].get_taxes_from_templates(
            tbai_maps.mapped("tax_template_ids")
        )
        for tax in self.tax_line_ids.filtered(
                lambda x: x.tax_id not in exclude_taxes):
            tax_subject_to = tax.tax_id.tbai_is_subject_to_tax()
            not_subject_to_cause = \
                not tax_subject_to and tax.tbai_get_value_causa() or ''
            is_exempted = tax_subject_to and tax.tax_id.tbai_is_tax_exempted() or False
            not_exempted_type = tax_subject_to and \
                not is_exempted and tax.tbai_get_value_tipo_no_exenta() or ''
            taxes.append((0, 0, {
                'base': tax.tbai_get_value_base_imponible(),
                'is_subject_to': tax_subject_to,
                'not_subject_to_cause': not_subject_to_cause,
                'is_exempted': is_exempted,
                'exempted_cause': is_exempted and tax.tbai_vat_exemption_key.code or '',
                'not_exempted_type': not_exempted_type,
                'amount': "%.2f" % abs(tax.tax_id.amount),
                'amount_total': tax.tbai_get_value_cuota_impuesto(),
                're_amount': tax.tbai_get_value_tipo_recargo_equivalencia() or '',
                're_amount_total':
                    tax.tbai_get_value_cuota_recargo_equivalencia() or '',
                'surcharge_or_simplified_regime':
                    tax.tbai_get_value_op_recargo_equivalencia_o_reg_simplificado(),
                'type': tax.tbai_get_value_tax_type()
            }))
        vals['tbai_tax_ids'] = taxes
        return vals

    @api.multi
    def _tbai_build_invoice(self):
        for record in self:
            vals = record.tbai_prepare_invoice_values()
            tbai_invoice = record.env['tbai.invoice'].create(vals)
            tbai_invoice.build_tbai_invoice()
            record.tbai_invoice_id = tbai_invoice.id

    def tbai_prepare_cancellation_values(self):
        self.ensure_one()
        cancel_datetime = self.date or self.invoice_date
        cancel_expedition_date = (
            self.tbai_expedition_date
            or self.tbai_get_value_fecha_expedicion_factura(
                invoice_datetime=cancel_datetime
            )
        )
        vals = {
            'cancelled_invoice_id': self.id,
            'schema': TicketBaiSchema.AnulaTicketBai.value,
            'name': "%s - %s" % (_("Cancellation"), self.number),
            'company_id': self.company_id.id,
            'number_prefix': self.tbai_get_value_serie_factura(),
            'number': self.tbai_get_value_num_factura(),
            'expedition_date': cancel_expedition_date
        }
        return vals

    @api.multi
    def _tbai_invoice_cancel(self):
        for record in self:
            vals = record.tbai_prepare_cancellation_values()
            tbai_invoice = record.env['tbai.invoice'].create(vals)
            tbai_invoice.build_tbai_invoice()
            record.tbai_cancellation_id = tbai_invoice.id

    @api.multi
    def action_cancel(self):
        non_cancelled_refunds = \
            self.mapped('refund_invoice_ids').filtered(lambda x: 'cancel' != x.state)
        if 0 < len(non_cancelled_refunds):
            raise exceptions.ValidationError(_(
                "You cannot cancel an invoice with non cancelled credit notes.\n"
                "Related invoices: %s") % ', '.join(
                x.number for x in non_cancelled_refunds))
        pending_invoices = self.filtered(
            lambda x: x.tbai_enabled and 'open' == x.state and
            x.tbai_invoice_id and
            TicketBaiInvoiceState.pending.value == x.tbai_invoice_id.state)
        if 0 < len(pending_invoices):
            raise exceptions.ValidationError(_(
                "You cannot cancel an invoice while being sent to the Tax Agency.\n"
                "Related invoices: %s") % ', '.join(x.number for x in pending_invoices))
        tbai_invoices = self.sudo().filtered(
            lambda x: x.tbai_enabled and x.state in ['open', 'in_payment', 'paid'] and
            x.tbai_invoice_id and
            TicketBaiInvoiceState.sent.value == x.tbai_invoice_id.state)
        tbai_invoices._tbai_invoice_cancel()
        return super().action_cancel()

    def _check_surcharge_invoice_lines(self):
        for record in self:
            if record.is_surcharge_or_simplified_regime_key():
                if record.error_surcharge_lines:
                    raise exceptions.ValidationError(_(
                        "There cannot be lines with and "
                        "without an equivalence "
                        "or simplified regime surcharge"
                        " on the same invoice."
                    ))
                no_surcharge_line_ids = record.invoice_line_ids.filtered(
                    lambda l:
                    l.product_id.has_equivalence_surcharge is False)
                if len(no_surcharge_line_ids) ==\
                   len(record.invoice_line_ids):
                    raise exceptions.ValidationError(_(
                        "If the key of the VAT regimes is equal "
                        "to 51 or 52, it "
                        "must be indicated that the operations are under the "
                        "equivalence surcharge or the simplified regime."
                    ))

    def _check_certificate_expiration(self):
        for invoice in self:
            if invoice.company_id.tbai_certificate_is_expired:
                expiration_date = invoice.company_id.tbai_expiration_date
                raise exceptions.ValidationError(
                    _("The certificate expired on %s") % expiration_date
                )

    @api.multi
    def invoice_validate(self):

        def validate_refund_invoices():
            for invoice in refund_invoices:
                valid_refund = True
                error_refund_msg = None
                if not invoice.refund_invoice_id and not invoice.tbai_refund_origin_ids:
                    valid_refund = False
                    error_refund_msg = _("Please, specify data for the original"
                                         " invoices that are going to be refunded")
                if invoice.refund_invoice_id.tbai_invoice_id:
                    valid_refund = invoice.refund_invoice_id.tbai_invoice_id.state in \
                        [
                            TicketBaiInvoiceState.pending.value,
                            TicketBaiInvoiceState.sent.value
                        ]
                    if not valid_refund:
                        error_refund_msg = _(
                            "Some of the original invoices have related tbai invoices "
                            "in inconsistent state please fix them beforehand.")
                if valid_refund and invoice.refund_invoice_id.tbai_cancellation_id:
                    valid_refund = False
                    error_refund_msg = _("Some of the original invoices "
                                         "have related tbai cancelled invoices")
                if not valid_refund:
                    raise exceptions.ValidationError(error_refund_msg)

        res = super().invoice_validate()
        self._check_certificate_expiration()
        self._check_surcharge_invoice_lines()
        # Credit Notes:
        # A. refund: creates a draft credit note, not validated from wizard.
        # B. cancel: creates a validated credit note from wizard
        # C. modify: creates a validated credit note and a draft invoice.
        #  * The draft invoice won't be a credit note 'by substitution',
        #  but a normal customer invoice.
        # There is no 'by substitution' credit note, only 'by differences'.
        tbai_invoices = self.sudo().env['account.invoice']
        tbai_invoices |= self.sudo().filtered(
            lambda x:
            x.tbai_enabled and 'out_invoice' == x.type and
            x.date and x.date >= x.journal_id.tbai_active_date)
        refund_invoices = \
            self.sudo().filtered(
                lambda x:
                x.tbai_enabled and 'out_refund' == x.type and
                (not x.tbai_refund_type or
                 x.tbai_refund_type == RefundType.differences.value) and
                x.date and x.date >= x.journal_id.tbai_active_date)

        validate_refund_invoices()
        tbai_invoices |= refund_invoices
        tbai_invoices._tbai_build_invoice()
        return res

    @api.model
    def _get_refund_common_fields(self):
        refund_common_fields = super()._get_refund_common_fields()
        refund_common_fields.append('company_id')
        return refund_common_fields

    def _prepare_tax_line_vals(self, line, tax):
        vals = super()._prepare_tax_line_vals(line, tax)
        if self.fiscal_position_id:
            exemption = self.fiscal_position_id.tbai_vat_exemption_ids.filtered(
                lambda e: e.tax_id.id == tax['id'])
            if 1 == len(exemption):
                vals['tbai_vat_exemption_key'] = exemption.tbai_vat_exemption_key.id
        return vals

    def tbai_is_invoice_refund(self):
        if 'out_refund' == self.type or (
                'out_invoice' == self.type and
                RefundType.substitution.value == self.tbai_refund_type):
            res = True
        else:
            res = False
        return res

    def _get_invoice_sequence(self):
        journal_id = self.journal_id
        if 'invoice_sequence_id' in journal_id:
            sequence = journal_id.refund_inv_sequence_id \
                if self.type == 'out_refund' and journal_id.refund_inv_sequence_id \
                else journal_id.invoice_sequence_id
        else:  # pragma: no cover
            sequence = journal_id.refund_sequence_id \
                if self.type == 'out_refund' else journal_id.sequence_id
        return sequence

    def tbai_get_value_serie_factura(self):
        sequence = self._get_invoice_sequence()
        prefix = sequence.with_context(
            ir_sequence_date=self.date_invoice,
            ir_sequence_date_range=self.date_invoice)._get_prefix_suffix()[0]
        return prefix

    def tbai_get_value_num_factura(self):
        invoice_prefix = self.tbai_get_value_serie_factura()
        if invoice_prefix and not self.number.startswith(
            invoice_prefix):
            raise exceptions.ValidationError(_(
                "Invoice Number Prefix %s is not part of Invoice Number %s!"
            ) % (invoice_prefix, self.number))
        return self.number[len(invoice_prefix):]

    def tbai_get_value_fecha_expedicion_factura(self, invoice_datetime=None):
        invoice_datetime = invoice_datetime or fields.Datetime.now()
        date = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(
            invoice_datetime))
        return date.strftime("%d-%m-%Y")

    def tbai_get_value_hora_expedicion_factura(self, invoice_datetime=None):
        invoice_datetime = invoice_datetime or fields.Datetime.now()
        date = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(
            invoice_datetime))
        return date.strftime("%H:%M:%S")

    def tbai_get_value_factura_emitida_sustitucion_simplificada(self):
        if self.tbai_substitute_simplified_invoice:
            res = SiNoType.S.value
        else:
            res = SiNoType.N.value
        return res

    def tbai_get_value_base_rectificada(self):
        return "%.2f" % abs(self.amount_untaxed_signed)

    def tbai_get_value_cuota_rectificada(self):
        amount = abs(self.amount_total_company_signed - self.amount_untaxed_signed)
        return "%.2f" % amount

    def tbai_get_value_fecha_operacion(self):
        return datetime.strptime(self.date or self.date_invoice, DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y")

    def tbai_get_value_retencion_soportada(self):
        tbai_maps = self.env["tbai.tax.map"].search(
            [('code', '=', "IRPF")]
        )
        irpf_taxes = self.env['l10n.es.aeat.report'].get_taxes_from_templates(
            tbai_maps.mapped("tax_template_ids")
        )
        taxes = self.tax_line_ids.filtered(
            lambda tax: tax.tax_id in irpf_taxes)
        if 0 < len(taxes):
            if RefundType.differences.value == self.tbai_refund_type:
                sign = 1
            else:
                sign = -1
            amount_total = sum(
                [tax.tbai_get_amount_total_company() for tax in taxes])
            res = "%.2f" % (sign * amount_total)
        else:
            res = None
        return res


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    def tbai_get_value_cantidad(self):
        if RefundType.differences.value == self.invoice_id.tbai_refund_type:
            sign = -1
        else:
            sign = 1
        return "%.2f" % float_round(sign * self.quantity, 2)

    def tbai_get_value_descuento(self):
        if self.discount:
            if RefundType.differences.value == self.invoice_id.tbai_refund_type:
                sign = -1
            else:
                sign = 1
            price_unit = self.price_unit / self.invoice_id.currency_id.with_context(
                dict(self._context or {}, date=self.invoice_id.date_invoice)).rate
            res = "%.2f" % (sign * self.quantity * price_unit * self.discount / 100.0)
        else:
            res = '0.00'
        return res

    def tbai_get_value_price_unit(self):
        if self.company_id.g5016:
            precision = self.env['decimal.precision'].precision_get(
                'Product Unit of Measure')
            qty = float(self.tbai_get_value_cantidad())
            if not float_is_zero(qty, precision_digits=precision):
                tbai_maps = self.env["tbai.tax.map"].search([('code', '=', "IRPF")])
                irpf_taxes = self.env['l10n.es.aeat.report'].get_taxes_from_templates(
                    tbai_maps.mapped("tax_template_ids"))
                line_tax = sum(
                    (self.invoice_line_tax_ids - irpf_taxes).mapped('amount'))
                amount_with_vat = float(self.tbai_get_value_importe_total())
                dto = float(self.tbai_get_value_descuento())
                fixed_unit_price = (amount_with_vat / (1 + line_tax / 100) + dto) / qty
                return "%.8f" % fixed_unit_price
        price_unit = self.price_unit / self.invoice_id.currency_id.with_context(
            dict(self._context or {}, date=self.invoice_id.date_invoice)).rate
        return "%.8f" % price_unit

    def tbai_get_value_importe_total(self):
        tbai_maps = self.env["tbai.tax.map"].search([('code', '=', "IRPF")])
        irpf_taxes = self.env['l10n.es.aeat.report'].get_taxes_from_templates(
            tbai_maps.mapped("tax_template_ids")
        )
        currency = self.company_id.currency_id or None
        price_total = self.price_total / self.invoice_id.currency_id.with_context(
            dict(self._context or {}, date=self.invoice_id.date_invoice)).rate
        # Recalculate price_total only if the line contains IRPF taxes
        if any(item in self.invoice_line_tax_ids.ids for item in irpf_taxes.ids):
            price_unit = self.price_unit / self.invoice_id.currency_id.with_context(
                dict(self._context or {}, date=self.invoice_id.date_invoice)).rate
            price_unit = price_unit * (1 - (self.discount or 0.0) / 100.0)
            taxes = (self.invoice_line_tax_ids - irpf_taxes).compute_all(
                price_unit, currency, self.quantity, product=self.product_id,
                partner=self.invoice_id.partner_id)
            price_total = taxes['total_included'] if taxes else price_total
        if RefundType.differences.value == self.invoice_id.tbai_refund_type:
            sign = -1
        else:
            sign = 1
        return "%.2f" % (sign * price_total)
