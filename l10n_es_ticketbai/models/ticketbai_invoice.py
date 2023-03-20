# Copyright 2021 Binovo IT Human Project SL
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.addons.l10n_es_ticketbai_api.models.ticketbai_invoice import \
    TicketBaiInvoiceState
from odoo.addons.l10n_es_ticketbai_api.ticketbai.xml_schema import TicketBaiSchema
from odoo import models, fields, api, exceptions, _


class TicketBAIInvoice(models.Model):
    _inherit = 'tbai.invoice'

    @api.multi
    def get_ticketbai_api(self, **kwargs):
        self.ensure_one()
        cert = self.company_id.tbai_certificate_get_public_key()
        key = self.company_id.tbai_certificate_get_private_key()
        return super().get_ticketbai_api(cert=cert, key=key, **kwargs)

    @api.multi
    def send(self, **kwargs):
        self.ensure_one()
        if TicketBaiSchema.TicketBai.value == self.schema and self.invoice_id:
            return super().send(invoice_id=self.invoice_id.id, **kwargs)
        elif TicketBaiSchema.AnulaTicketBai.value == self.schema and \
                self.cancelled_invoice_id:
            return super().send(invoice_id=self.cancelled_invoice_id.id, **kwargs)
        else:
            return super().send(**kwargs)


class TicketBAIInvoiceRefundOrigin(models.Model):
    _name = 'tbai.invoice.refund.origin'
    _description = 'TicketBAI Refunded Invoices Origin Invoice Data'

    account_refund_invoice_id = fields.Many2one(comodel_name='account.invoice',
                                                domain=[('type', '=', 'out_refund')],
                                                required=True)
    number = fields.Char(
        required=True,
        help='The number of the invoice name e.g. if the invoice name is '
        'INV/2021/00001 then the number is 00001')
    number_prefix = fields.Char(
        default='',
        help='Number prefix of this invoice name e.g. if the invoice name is'
        ' INV/2021/00001 then the prefix is INV/2021/, '
        'ending back slash included')
    expedition_date = fields.Date(
        required=True)

    @api.multi
    @api.constrains('number')
    def _check_number(self):
        for record in self:
            if 20 < len(record.number):
                raise exceptions.ValidationError(_(
                    "Refunded Invoice Number %s longer than expected. "
                    "Should be 20 characters max.!"
                ) % record.number)

    @api.multi
    @api.constrains('number_prefix')
    def _check_number_prefix(self):
        for record in self:
            if record.number_prefix and 20 < len(record.number_prefix):
                raise exceptions.ValidationError(_(
                    "Refunded Invoice %s Number Prefix %s longer than expected. "
                    "Should be 20 characters max.!"
                ) % (record.number, record.number_prefix))
