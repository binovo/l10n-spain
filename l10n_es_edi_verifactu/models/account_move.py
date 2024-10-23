# -*- coding: utf-8 -*-
# Copyright 2024 Binovo IT Human Project SL
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from base64 import b64encode, b64decode
from lxml import etree
from odoo import models, fields, api
from urllib.parse import urlencode
from ..lib.aeat import NAMESPACE_SUM1_INFO, aeat_qr_url


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
            base_url = aeat_qr_url(move)
            xml_node = move.get_l10n_es_edi_verifactu_xml()
            values = {
                "nif": xml_node.xpath(
                    "//sum1:IDFactura/sum1:IDEmisorFactura",
                    namespaces=NAMESPACE_SUM1_INFO,
                )[0].text,
                "numserie": xml_node.xpath(
                    "//sum1:IDFactura/sum1:NumSerieFactura",
                    namespaces=NAMESPACE_SUM1_INFO,
                )[0].text,
                "fecha": xml_node.xpath(
                    "//sum1:IDFactura/sum1:FechaExpedicionFactura",
                    namespaces=NAMESPACE_SUM1_INFO,
                )[0].text,
                "importe": xml_node.xpath(
                    "//sum1:ImporteTotal", namespaces=NAMESPACE_SUM1_INFO
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
                ".//sum1:IDFactura/sum1:NumSerieFactura[text()='%s']/following::sum1:FechaExpedicionFactura"
                % self.name,
                namespaces=xml_root_node.nsmap,
            )[0].text
            return xml_issued_time
        else:
            return xml_root_node

    def get_verifactu_hash_from_xml(self):
        self.ensure_one()
        xml_root_node = self.get_l10n_es_edi_verifactu_xml()
        if xml_root_node is not None:
            xml_hash = xml_root_node.xpath(
                ".//sum1:IDFactura/sum1:NumSerieFactura[text()='%s']/following::sum1:TipoHuella/following::sum1:Huella"
                % self.name,
                namespaces=xml_root_node.nsmap,
            )[0].text
            return xml_hash
        else:
            return xml_root_node

    def get_verifactu_issuer_vat_from_xml(self):
        self.ensure_one()
        xml_root_node = self.get_l10n_es_edi_verifactu_xml()
        if xml_root_node is not None:
            xml_issuer_vat = xml_root_node.xpath(
                ".//sum1:IDFactura/sum1:NumSerieFactura[text()='%s']/parent::sum1:IDFactura/sum1:IDEmisorFactura"
                % self.name,
                namespaces=xml_root_node.nsmap,
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

    # OVERRIDEN FUNCTIONS
    def _post(self, soft=True):
        """Add context variable to ensure that Verifactu-XML file is created when calling _check_move_configuration
        only from this post method, we want to avoid the Verifactu-XML file creation in other
        _check_move_configuration method calls.
        """
        return super(
            AccountMove, self.with_context(l10n_es_verifactu_get_xml=True)
        )._post(soft=soft)
