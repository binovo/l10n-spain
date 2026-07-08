# -*- coding: utf-8 -*-
# Copyright 2024 Binovo IT Human Project SL
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from base64 import b64encode, b64decode
from lxml import etree
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from urllib.parse import urlencode
from .account_edi_format import NAMESPACE_SF_INFO


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_es_edi_verifactu_is_required = fields.Boolean(
        string="Is the Spanish Verifactu needed",
        compute="_compute_l10n_es_edi_verifactu_is_required",
    )
    l10n_es_edi_verifactu_chain_index = fields.Integer(
        string="Verifactu chain index", copy=False, readonly=True
    )
    l10n_es_edi_verifactu_xml = fields.Binary(
        attachment=True, readonly=True, copy=False, string="Verifactu XML"
    )
    l10n_es_edi_verifactu_cancel_xml = fields.Binary(
        attachment=True, readonly=True, copy=False, string="Verifactu cancel XML"
    )
    l10n_es_edi_verifactu_qr_url = fields.Char(
        string="Verifactu QR URL", compute="_compute_l10n_es_edi_verifactu_qr_url"
    )
    l10n_es_edi_verifactu_refund_origin_ids = fields.One2many(
        comodel_name="account.move.vf.refund.origin",
        inverse_name="invoice_id",
        string="Refund origin references",
    )

    @api.depends("move_type", "company_id")
    def _compute_l10n_es_edi_verifactu_is_required(self):
        for move in self:
            move.l10n_es_edi_verifactu_is_required = (
                move.is_sale_document()
                and move.country_code == "ES"
                and move.company_id.l10n_es_verifactu_enabled
            )

    def _compute_l10n_es_edi_verifactu_qr_url(self):
        for move in self.filtered(lambda m: m.has_verifactu_xml_and_chain_index()):
            base_url = self.env["account.edi.format"]._l10n_es_verifactu_aeat_qr_url(
                move
            )
            xml_node = move.get_l10n_es_edi_verifactu_xml()
            values = {
                "nif": xml_node.xpath(
                    "//sf:IDFactura/sf:IDEmisorFactura",
                    namespaces=NAMESPACE_SF_INFO,
                )[0].text,
                "numserie": xml_node.xpath(
                    "//sf:IDFactura/sf:NumSerieFactura",
                    namespaces=NAMESPACE_SF_INFO,
                )[0].text,
                "fecha": xml_node.xpath(
                    "//sf:IDFactura/sf:FechaExpedicionFactura",
                    namespaces=NAMESPACE_SF_INFO,
                )[0].text,
                "importe": xml_node.xpath(
                    "//sf:ImporteTotal", namespaces=NAMESPACE_SF_INFO
                )[0].text,
            }
            move.l10n_es_edi_verifactu_qr_url = "%s?%s" % (
                base_url,
                urlencode(values, encoding="utf-8"),
            )

    def get_l10n_es_edi_verifactu_xml(self, cancel=False):
        self.ensure_one()
        doc = (
            self.l10n_es_edi_verifactu_cancel_xml
            if cancel
            else self.l10n_es_edi_verifactu_xml
        )
        if not doc:
            return None
        return etree.fromstring(b64decode(doc))

    def update_l10n_es_edi_verifactu_xml(self, xml_doc, cancel):
        self.ensure_one()
        b64_doc = (
            b""
            if xml_doc is None
            else b64encode(etree.tostring(xml_doc, encoding="UTF-8"))
        )
        if cancel:
            self.l10n_es_edi_verifactu_cancel_xml = b64_doc
        else:
            self.l10n_es_edi_verifactu_xml = b64_doc

    def get_verifactu_issued_time_from_xml(self):
        self.ensure_one()
        xml_root_node = self.get_l10n_es_edi_verifactu_xml()
        if xml_root_node is not None:
            xml_issued_time = xml_root_node.xpath(
                ".//sf:FechaHoraHusoGenRegistro", namespaces=NAMESPACE_SF_INFO
            )[0].text
            return xml_issued_time
        else:
            return None

    def get_verifactu_hash_from_xml(self):
        self.ensure_one()
        xml_root_node = self.get_l10n_es_edi_verifactu_xml()
        if xml_root_node is not None:
            xml_hash = xml_root_node.xpath(
                ".//sf:IDFactura/sf:NumSerieFactura[text()='%s']/following::sf:TipoHuella/following::sf:Huella"
                % self.name,
                namespaces=NAMESPACE_SF_INFO,
            )[0].text
            return xml_hash
        else:
            return xml_root_node

    def get_verifactu_issuer_vat_from_xml(self):
        self.ensure_one()
        xml_root_node = self.get_l10n_es_edi_verifactu_xml()
        if xml_root_node is not None:
            xml_issuer_vat = xml_root_node.xpath(
                ".//sf:IDFactura/sf:NumSerieFactura[text()='%s']/parent::sf:IDFactura/sf:IDEmisorFactura"
                % self.name,
                namespaces=NAMESPACE_SF_INFO,
            )[0].text
            return xml_issuer_vat
        else:
            return xml_root_node

    def has_verifactu_xml_and_chain_index(self):
        self.ensure_one()
        verifactu_post_xml = (
            self.l10n_es_edi_verifactu_xml or self.l10n_es_edi_verifactu_cancel_xml
        )
        return verifactu_post_xml and self.l10n_es_edi_verifactu_chain_index

    def l10n_es_verifactu_is_in_chain(self):
        self.ensure_one()
        verifactu_doc_ids = self.edi_document_ids.filtered(
            lambda d: d.edi_format_id.code == "es_verifactu"
        )
        return (
            self.l10n_es_edi_verifactu_is_required
            and self.has_verifactu_xml_and_chain_index()
            and verifactu_doc_ids
        )

    def l10n_es_verifactu_allows_repercuted_recargo(self):
        """Allow repercuted recargo only for general-regime sales with recargo taxes."""
        self.ensure_one()
        if not self.is_sale_document():
            return False
        if not self.company_id.l10n_es_verifactu_is_general_regime():
            return False
        return bool(
            self.invoice_line_ids.tax_ids.filtered(
                lambda tax: tax.l10n_es_type == "recargo"
            )
        )

    # OVERRIDEN FUNCTIONS
    def _post(self, soft=True):
        """Add context variable to ensure that Verifactu-XML file is created when calling _check_move_configuration
        only from this post method, we want to avoid the Verifactu-XML file creation in other
        _check_move_configuration method calls.
        """
        verifactu_moves = self.filtered("l10n_es_edi_verifactu_is_required")
        for company in verifactu_moves.mapped("company_id"):
            company._lock_verifactu_chain()
        return super(
            AccountMove, self.with_context(l10n_es_verifactu_get_xml=True)
        )._post(soft=soft)


class AccountMoveVFRefundOrigin(models.Model):
    _name = "account.move.vf.refund.origin"
    _description = "Refunded invoices origin data"

    invoice_id = fields.Many2one(
        comodel_name="account.move", domain=[("type", "=", "out_refund")], required=True
    )
    number = fields.Char(
        required=True,
        help="Enter the full invoice identifier, including series and year if applicable.",
    )
    expedition_date = fields.Date(required=True)

    @api.constrains("number")
    def _check_number(self):
        for record in self:
            if 60 < len(record.number):
                raise ValidationError(
                    _(
                        "Refunded Invoice Number %s longer than expected. "
                        "Should be 60 characters max.!"
                    )
                    % record.number
                )
