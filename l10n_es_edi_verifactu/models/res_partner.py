# -*- coding: utf-8 -*-
# Copyright 2025 Binovo IT Human Project SL
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo import exceptions
from odoo.tools import config

VERIFACTU_ID_TYPE = {
    "vat": "02",
    "passport": "03",
    "residence_country": "04",
    "residence_certificate": "05",
    "other": "06",
}


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_es_edi_verifactu_partner_id_type = fields.Selection(
        [
            (VERIFACTU_ID_TYPE.get("vat"), "VAT identification number"),
            (VERIFACTU_ID_TYPE.get("passport"), "Passport"),
            (
                VERIFACTU_ID_TYPE.get("residence_country"),
                "Official identification document issued by the country or territory of residence",
            ),
            (
                VERIFACTU_ID_TYPE.get("residence_certificate"),
                "Residence certificate",
            ),
            (VERIFACTU_ID_TYPE.get("other"), "Other document"),
        ],
        string="Verifactu Identification Type Code",
    )

    def is_spanish(self):
        self.ensure_one()
        return self.country_id.code == self.env.ref("base.es").code

    def l10n_es_edi_verifactu_is_vat_id_type(self):
        self.ensure_one()
        return (
            not self.l10n_es_edi_verifactu_partner_id_type
            or self.l10n_es_edi_verifactu_partner_id_type
            == VERIFACTU_ID_TYPE.get("vat")
        )

    def l10n_es_edi_verifactu_is_spanish_nif(self):
        self.ensure_one()
        return self.is_spanish() and self.l10n_es_edi_verifactu_is_vat_id_type()

    def is_from_eu(self):
        self.ensure_one()
        return self.country_id.code in self.env.ref("base.europe").country_ids.mapped(
            "code"
        )

    def check_l10n_es_edi_verifactu_spanish_id_type(self):
        for partner in self:
            if (
                partner.is_spanish()
                and partner.l10n_es_edi_verifactu_partner_id_type
                not in [
                    VERIFACTU_ID_TYPE.get("vat"),
                    VERIFACTU_ID_TYPE.get("passport"),
                ]
            ):
                raise exceptions.ValidationError(
                    _(
                        "Identification type can only be NIF or Passport for Spanish partners."
                    )
                )

    def check_l10n_es_edi_verifactu_non_eu_id_type(self):
        for partner in self:
            if (
                not partner.is_from_eu()
                and partner.l10n_es_edi_verifactu_is_vat_id_type()
            ):
                raise exceptions.ValidationError(
                    _("Identification type can not be NIF for non-community partners.")
                )

    @api.constrains("l10n_es_edi_verifactu_partner_id_type")
    def check_l10n_es_edi_verifactu_partner_id_type(self):
        for partner in self.filtered(
            lambda p: p.country_id and p.l10n_es_edi_verifactu_partner_id_type
        ):
            partner.check_l10n_es_edi_verifactu_spanish_id_type()
            partner.check_l10n_es_edi_verifactu_non_eu_id_type()

    @api.constrains("vat", "l10n_es_edi_verifactu_partner_id_type")
    def check_vat(self):
        for partner in self:
            check_vat = partner.l10n_es_edi_verifactu_is_vat_id_type()
            if config["test_enable"]:
                check_vat = not bool(
                    self.env.context.get("test_not_verifactu_vat_partner_id_type")
                )
            if check_vat:
                super().check_vat()
            else:
                if partner.vat and 20 < len(partner.vat):
                    raise exceptions.ValidationError(
                        _(
                            "Partner Identification Number %s longer than expected. "
                            "Should be 20 characters max.!"
                        )
                        % partner.name
                    )
