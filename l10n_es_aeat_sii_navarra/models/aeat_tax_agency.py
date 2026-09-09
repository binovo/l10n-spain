# Copyright 2026 Binovo IT Human Project SL
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models

SII_WDSL_MAPPING = {
    "out_invoice": "sii_wsdl_out",
    "out_refund": "sii_wsdl_out",
    "in_invoice": "sii_wsdl_in",
    "in_refund": "sii_wsdl_in",
}
SII_PORT_NAME_MAPPING = {
    "out_invoice": "SuministroFactEmitidas",
    "out_refund": "SuministroFactEmitidas",
    "in_invoice": "SuministroFactRecibidas",
    "in_refund": "SuministroFactRecibidas",
}


class AeatTaxAgency(models.Model):
    _inherit = "aeat.tax.agency"

    def _connect_params_sii(self, mapping_key, company):
        self.ensure_one()
        agency_navarra = self.env.ref("l10n_es_aeat.aeat_tax_agency_navarra")
        if self != agency_navarra:
            return super()._connect_params_sii(mapping_key, company)
        wsdl_field = SII_WDSL_MAPPING[mapping_key]
        wsdl_test_field = wsdl_field + "_test_address"
        port_name = SII_PORT_NAME_MAPPING[mapping_key]
        address = getattr(self, wsdl_test_field) if company.sii_test else False
        if not address and company.sii_test:
            # If not test address is provides we try to get it using the port name.
            port_name += "Pruebas"
        return {
            "wsdl": getattr(
                self.env.ref("l10n_es_aeat.aeat_tax_agency_spain"), wsdl_field
            ),
            "address": getattr(self, wsdl_field),
            "port_name": port_name,
        }
