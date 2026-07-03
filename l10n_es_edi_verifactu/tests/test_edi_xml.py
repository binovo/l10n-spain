# -*- coding: utf-8 -*-
# Copyright 2024 Binovo IT Human Project SL
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime
from freezegun import freeze_time
from lxml import etree
from pytz import timezone
from .common import TestEdiVerifactuCommon
from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools.xml_utils import validate_xml_from_attachment
from ..models.account_edi_format import (
    NAMESPACE_SF_INFO,
    NAMESPACE_SFLR_INFO,
    TEST_AEAT_VERIFACTU_QR_URL,
)
from ..models.res_partner import VERIFACTU_ID_TYPE
from odoo.addons.l10n_es_edi_verifactu.utils.constants import (
    VERIFACTU_VAT_REGIME_EQUIVALENCE_SURCHARGE,
)

from .test_xml_post_data import (
    SPANISH_INVOICE_XML_POST,
    SPANISH_INVOICE_EQUIVALENCE_SURCHARGE_XML_POST,
    RECARGO_EQUIVALENCE_SURCHARGE_CUSTOMER_XML_POST,
    REFUND_INVOICE_XML_POST,
    EU_INVOICE_XML_POST,
    NON_EU_INVOICE_XML_POST,
    CANCEL_SPANISH_INVOICE_XML_POST,
    MULTI_CURRENCY_INVOICE_XML_POST,
    PASSPORT_SPANISH_INVOICE_XML_POST,
    REFUND_ORIGIN_INVOICE_XML_POST,
)


@tagged("post_install", "-at_install", "post_install_l10n")
class TestEdiVerifactuXML(TestEdiVerifactuCommon):
    def setUp(self):
        super().setUp()
        # sudo() why: ir.config_parameter is only accessible for base.group_system
        SudoParam = self.env["ir.config_parameter"].sudo()
        SudoParam.set_param(
            "l10n_es_edi_verifactu.verifactu_developer_name", "ODOO BINOVO"
        )
        SudoParam.set_param("l10n_es_edi_verifactu.verifactu_developer_id", "19960488F")
        SudoParam.set_param("l10n_es_edi_verifactu.verifactu_software_id", "22")
        SudoParam.set_param(
            "l10n_es_edi_verifactu.verifactu_software_name", "BINOVOFACTU"
        )
        SudoParam.set_param("l10n_es_edi_verifactu.verifactu_software_number", "123")
        SudoParam.set_param("l10n_es_edi_verifactu.verifactu_software_version", "16.0")
        self.operation_date = datetime(
            year=2024,
            month=10,
            day=28,
            hour=0,
            minute=0,
            second=0,
            tzinfo=timezone("utc"),
        )
        self.spanish_invoice = (
            self.env["account.move"]
            .with_context(edi_test_mode=True)
            .create(
                {
                    "move_type": "out_invoice",
                    "partner_id": self.env.ref(
                        "l10n_es_edi_verifactu.l10n_es_verifactu_partner_sp_uztapide"
                    ).id,
                    "fiscal_position_id": self.env.ref(
                        f"l10n_es.{self.env.company.id}_fp_nacional"
                    ).id,
                    "invoice_date": self.operation_date,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.env.ref(
                                    "product.product_product_7"
                                ).id,
                                "price_unit": 1000.0,
                                "quantity": 5,
                                "discount": 20.0,
                                "tax_ids": [
                                    (
                                        6,
                                        0,
                                        self.env.ref(
                                            f"l10n_es.{self.env.company.id}_account_tax_template_s_iva21b"
                                        ).ids,
                                    )
                                ],
                            },
                        )
                    ],
                }
            )
        )
        self.recargo_invoice = (
            self.env["account.move"]
            .with_context(edi_test_mode=True)
            .create(
                {
                    "move_type": "out_invoice",
                    "partner_id": self.env.ref(
                        "l10n_es_edi_verifactu.l10n_es_verifactu_partner_sp_uztapide"
                    ).id,
                    "fiscal_position_id": self.env.ref(
                        f"l10n_es.{self.env.company.id}_fp_recargo"
                    ).id,
                    "invoice_date": self.operation_date,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "product_id": self.env.ref(
                                    "product.product_product_7"
                                ).id,
                                "price_unit": 150.0,
                                "quantity": 1,
                                "tax_ids": [
                                    Command.set(
                                        [
                                            self.env.ref(
                                                f"l10n_es.{self.env.company.id}_account_tax_template_s_iva10b"
                                            ).id,
                                            self.env.ref(
                                                f"l10n_es.{self.env.company.id}_account_tax_template_s_req014"
                                            ).id,
                                        ]
                                    )
                                ],
                            }
                        ),
                        Command.create(
                            {
                                "product_id": self.env.ref(
                                    "product.product_product_8"
                                ).id,
                                "price_unit": 300.0,
                                "quantity": 1,
                                "tax_ids": [
                                    Command.set(
                                        [
                                            self.env.ref(
                                                f"l10n_es.{self.env.company.id}_account_tax_template_s_iva21b"
                                            ).id,
                                            self.env.ref(
                                                f"l10n_es.{self.env.company.id}_account_tax_template_s_req52"
                                            ).id,
                                        ]
                                    )
                                ],
                            }
                        ),
                    ],
                }
            )
        )
        self.eu_invoice = (
            self.env["account.move"]
            .with_context(edi_test_mode=True)
            .create(
                {
                    "move_type": "out_invoice",
                    "partner_id": self.env.ref(
                        "l10n_es_edi_verifactu.l10n_es_verifactu_partner_fr"
                    ).id,
                    "fiscal_position_id": self.env.ref(
                        f"l10n_es.{self.env.company.id}_fp_intra"
                    ).id,
                    "invoice_date": self.operation_date,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.env.ref(
                                    "product.product_product_7"
                                ).id,
                                "price_unit": 1000.0,
                                "quantity": 5,
                                "discount": 20.0,
                                "tax_ids": [
                                    (
                                        6,
                                        0,
                                        self.env.ref(
                                            f"l10n_es.{self.env.company.id}_account_tax_template_s_iva0_ic"
                                        ).ids,
                                    )
                                ],
                            },
                        ),
                    ],
                }
            )
        )
        self.non_eu_invoice = (
            self.env["account.move"]
            .with_context(edi_test_mode=True)
            .create(
                {
                    "move_type": "out_invoice",
                    "partner_id": self.env.ref(
                        "l10n_es_edi_verifactu.l10n_es_verifactu_partner_ad"
                    ).id,
                    "fiscal_position_id": self.env.ref(
                        f"l10n_es.{self.env.company.id}_fp_extra"
                    ).id,
                    "invoice_date": self.operation_date,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.env.ref(
                                    "product.product_product_7"
                                ).id,
                                "price_unit": 1000.0,
                                "quantity": 5,
                                "discount": 20.0,
                                "tax_ids": [
                                    (
                                        6,
                                        0,
                                        self.env.ref(
                                            f"l10n_es.{self.env.company.id}_account_tax_template_s_iva0_e"
                                        ).ids,
                                    )
                                ],
                            },
                        ),
                    ],
                }
            )
        )
        self.currency_usd = self.env.ref("base.USD")
        self.currency_usd.active = True
        self.env["res.currency.rate"].create(
            {
                "name": self.operation_date,
                "company_id": self.env.company.id,
                "currency_id": self.currency_usd.id,
                "rate": 0.5,
            }
        )
        self.multi_currency_invoice = (
            self.env["account.move"]
            .with_context(edi_test_mode=True)
            .create(
                {
                    "move_type": "out_invoice",
                    "partner_id": self.env.ref(
                        "l10n_es_edi_verifactu.l10n_es_verifactu_partner_sp_uztapide"
                    ).id,
                    "fiscal_position_id": self.env.ref(
                        f"l10n_es.{self.env.company.id}_fp_nacional"
                    ).id,
                    "currency_id": self.currency_usd.id,
                    "invoice_date": self.operation_date,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.env.ref(
                                    "product.product_product_7"
                                ).id,
                                "price_unit": 1000.0,
                                "quantity": 5,
                                "discount": 20.0,
                                "tax_ids": [
                                    (
                                        6,
                                        0,
                                        self.env.ref(
                                            f"l10n_es.{self.env.company.id}_account_tax_template_s_iva21b"
                                        ).ids,
                                    )
                                ],
                            },
                        ),
                    ],
                }
            )
        )

    def test_check_move_configuration(self):
        self.env.ref(
            "l10n_es_edi_verifactu.edi_es_verifactu"
        )._check_move_configuration(self.spanish_invoice)
        self.assertFalse(self.spanish_invoice.l10n_es_edi_verifactu_xml)
        self.assertFalse(self.spanish_invoice.l10n_es_edi_verifactu_chain_index)
        self.env.ref("l10n_es_edi_verifactu.edi_es_verifactu").with_context(
            l10n_es_verifactu_get_xml=True
        )._check_move_configuration(self.spanish_invoice)
        self.assertTrue(self.spanish_invoice.l10n_es_edi_verifactu_xml)
        self.assertTrue(self.spanish_invoice.l10n_es_edi_verifactu_chain_index)

    def test_create_spanish_recipient_national_fp(self):
        with freeze_time(self.operation_date):
            self.spanish_invoice.action_post()
            verifactu_xml = self.env["account.edi.format"]._l10n_es_verifactu_get_xml(
                self.spanish_invoice
            )
            validate_xml_from_attachment(
                self.env, verifactu_xml, "soap-envelope.xsd", prefix="l10n_es_verifactu"
            )
            invoice_records_node = verifactu_xml.xpath(
                ".//sfLR:RegFactuSistemaFacturacion", namespaces=NAMESPACE_SFLR_INFO
            )[0]
            validate_xml_from_attachment(
                self.env,
                invoice_records_node,
                "SuministroLR.xsd",
                prefix="l10n_es_verifactu",
            )
            xml_expected = etree.fromstring(SPANISH_INVOICE_XML_POST)
            self.assertXmlTreeEqual(verifactu_xml, xml_expected)

    def test_create_spanish_recipient_equivalence_surcharge_regime(self):
        """F1 with company in RE regime (18): VAT only, no repercuted recargo."""
        self.company_data["company"].l10n_es_verifactu_vat_regime_key = (
            VERIFACTU_VAT_REGIME_EQUIVALENCE_SURCHARGE
        )
        with freeze_time(self.operation_date):
            self.spanish_invoice.action_post()
            verifactu_xml = self.env["account.edi.format"]._l10n_es_verifactu_get_xml(
                self.spanish_invoice
            )
            validate_xml_from_attachment(
                self.env, verifactu_xml, "soap-envelope.xsd", prefix="l10n_es_verifactu"
            )
            invoice_records_node = verifactu_xml.xpath(
                ".//sfLR:RegFactuSistemaFacturacion", namespaces=NAMESPACE_SFLR_INFO
            )[0]
            validate_xml_from_attachment(
                self.env,
                invoice_records_node,
                "SuministroLR.xsd",
                prefix="l10n_es_verifactu",
            )
            xml_expected = etree.fromstring(
                SPANISH_INVOICE_EQUIVALENCE_SURCHARGE_XML_POST
            )
            self.assertXmlTreeEqual(verifactu_xml, xml_expected)

    def test_create_re_customer_recargo_invoice(self):
        """F1 repercuting recargo to an RE customer with 10% and 21% VAT."""
        with freeze_time(self.operation_date):
            self.recargo_invoice.action_post()
            verifactu_xml = self.env["account.edi.format"]._l10n_es_verifactu_get_xml(
                self.recargo_invoice
            )
            validate_xml_from_attachment(
                self.env, verifactu_xml, "soap-envelope.xsd", prefix="l10n_es_verifactu"
            )
            invoice_records_node = verifactu_xml.xpath(
                ".//sfLR:RegFactuSistemaFacturacion", namespaces=NAMESPACE_SFLR_INFO
            )[0]
            validate_xml_from_attachment(
                self.env,
                invoice_records_node,
                "SuministroLR.xsd",
                prefix="l10n_es_verifactu",
            )
            xml_expected = etree.fromstring(
                RECARGO_EQUIVALENCE_SURCHARGE_CUSTOMER_XML_POST
            )
            xml_expected.xpath("//sf:NumSerieFactura", namespaces=NAMESPACE_SF_INFO)[
                0
            ].text = self.recargo_invoice.name
            self.assertXmlTreeEqual(verifactu_xml, xml_expected)

    def test_regime_18_rejects_repercuted_recargo(self):
        """Repercuted recargo is rejected when the company is in RE regime (18)."""
        self.company_data["company"].write(
            {
                "l10n_es_verifactu_vat_regime_key": (
                    VERIFACTU_VAT_REGIME_EQUIVALENCE_SURCHARGE
                ),
                "l10n_es_verifactu_enabled": True,
            }
        )
        recargo_taxes = self.recargo_invoice.invoice_line_ids.tax_ids.filtered(
            lambda tax: tax.l10n_es_type == "recargo"
        )
        self.assertTrue(recargo_taxes)
        with freeze_time(self.operation_date):
            with self.assertRaisesRegex(ValidationError, "not supported invoice taxes"):
                self.recargo_invoice.action_post()
        self.assertFalse(self.recargo_invoice.l10n_es_edi_verifactu_xml)

    def test_create_refund_invoice(self):
        with freeze_time(self.operation_date):
            self.spanish_invoice.action_post()
            move_reversal = (
                self.env["account.move.reversal"]
                .with_context(
                    active_model="account.move", active_ids=self.spanish_invoice.ids
                )
                .create(
                    {
                        "date": self.operation_date,
                        "reason": "A reason",
                        "refund_method": "refund",
                        "journal_id": self.spanish_invoice.journal_id.id,
                    }
                )
            )
            reversal = move_reversal.reverse_moves()
            refund_invoice = self.env["account.move"].browse(reversal["res_id"])
            verifactu_xml = self.env["account.edi.format"]._l10n_es_verifactu_get_xml(
                refund_invoice
            )
            validate_xml_from_attachment(
                self.env, verifactu_xml, "soap-envelope.xsd", prefix="l10n_es_verifactu"
            )
            invoice_records_node = verifactu_xml.xpath(
                ".//sfLR:RegFactuSistemaFacturacion", namespaces=NAMESPACE_SFLR_INFO
            )[0]
            validate_xml_from_attachment(
                self.env,
                invoice_records_node,
                "SuministroLR.xsd",
                prefix="l10n_es_verifactu",
            )
            xml_expected = etree.fromstring(REFUND_INVOICE_XML_POST)
            self.assertXmlTreeEqual(verifactu_xml, xml_expected)

    def test_create_refund_origin_invoice(self):
        with freeze_time(self.operation_date):
            refund_invoice = self.env["account.move"].create(
                {
                    "move_type": "out_refund",
                    "invoice_date": self.operation_date,
                    "date": self.operation_date,
                    "journal_id": self.spanish_invoice.journal_id.id,
                    "partner_id": self.env.ref(
                        "l10n_es_edi_verifactu.l10n_es_verifactu_partner_sp_uztapide"
                    ).id,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.env.ref(
                                    "product.product_product_7"
                                ).id,
                                "quantity": 4,
                                "price_unit": 1000.0,
                                "tax_ids": [
                                    (
                                        6,
                                        0,
                                        self.env.ref(
                                            f"l10n_es.{self.env.company.id}_account_tax_template_s_iva21b"
                                        ).ids,
                                    )
                                ],
                            },
                        )
                    ],
                    "l10n_es_edi_verifactu_refund_origin_ids": [
                        (
                            0,
                            0,
                            {
                                "number": "INV/2023/00019",
                                "expedition_date": "2023-09-19",
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "number": "INV/2023/00082",
                                "expedition_date": "2023-05-05",
                            },
                        ),
                    ],
                }
            )
            verifactu_xml = self.env["account.edi.format"]._l10n_es_verifactu_get_xml(
                refund_invoice
            )
            validate_xml_from_attachment(
                self.env, verifactu_xml, "soap-envelope.xsd", prefix="l10n_es_verifactu"
            )
            invoice_records_node = verifactu_xml.xpath(
                ".//sfLR:RegFactuSistemaFacturacion", namespaces=NAMESPACE_SFLR_INFO
            )[0]
            validate_xml_from_attachment(
                self.env,
                invoice_records_node,
                "SuministroLR.xsd",
                prefix="l10n_es_verifactu",
            )
            xml_expected = etree.fromstring(REFUND_ORIGIN_INVOICE_XML_POST)
            self.assertXmlTreeEqual(verifactu_xml, xml_expected)

    def test_create_eu_recipient_intra_fp(self):
        with freeze_time(self.operation_date):
            self.eu_invoice.action_post()
            verifactu_xml = self.env["account.edi.format"]._l10n_es_verifactu_get_xml(
                self.eu_invoice
            )
            validate_xml_from_attachment(
                self.env, verifactu_xml, "soap-envelope.xsd", prefix="l10n_es_verifactu"
            )
            invoice_records_node = verifactu_xml.xpath(
                ".//sfLR:RegFactuSistemaFacturacion", namespaces=NAMESPACE_SFLR_INFO
            )[0]
            validate_xml_from_attachment(
                self.env,
                invoice_records_node,
                "SuministroLR.xsd",
                prefix="l10n_es_verifactu",
            )
            xml_expected = etree.fromstring(EU_INVOICE_XML_POST)
            self.assertXmlTreeEqual(verifactu_xml, xml_expected)

    def test_create_non_eu_invoice_invoice(self):
        with freeze_time(self.operation_date):
            self.non_eu_invoice.action_post()
            verifactu_xml = self.env["account.edi.format"]._l10n_es_verifactu_get_xml(
                self.non_eu_invoice
            )
            validate_xml_from_attachment(
                self.env, verifactu_xml, "soap-envelope.xsd", prefix="l10n_es_verifactu"
            )
            invoice_records_node = verifactu_xml.xpath(
                ".//sfLR:RegFactuSistemaFacturacion", namespaces=NAMESPACE_SFLR_INFO
            )[0]
            validate_xml_from_attachment(
                self.env,
                invoice_records_node,
                "SuministroLR.xsd",
                prefix="l10n_es_verifactu",
            )
            xml_expected = etree.fromstring(NON_EU_INVOICE_XML_POST)
            self.assertXmlTreeEqual(verifactu_xml, xml_expected)

    def test_create_passport_spanish_recipient_national_fp(self):
        with freeze_time(self.operation_date):
            partner = self.env.ref(
                "l10n_es_edi_verifactu.l10n_es_verifactu_partner_sp_uztapide"
            )
            partner.with_context(test_not_verifactu_vat_partner_id_type=True).write(
                {
                    "l10n_es_edi_verifactu_partner_id_type": VERIFACTU_ID_TYPE.get(
                        "passport"
                    ),
                    "vat": "H5734582F",
                }
            )
            self.spanish_invoice.action_post()
            verifactu_xml = self.env["account.edi.format"]._l10n_es_verifactu_get_xml(
                self.spanish_invoice
            )
            validate_xml_from_attachment(
                self.env, verifactu_xml, "soap-envelope.xsd", prefix="l10n_es_verifactu"
            )
            invoice_records_node = verifactu_xml.xpath(
                ".//sfLR:RegFactuSistemaFacturacion", namespaces=NAMESPACE_SFLR_INFO
            )[0]
            validate_xml_from_attachment(
                self.env,
                invoice_records_node,
                "SuministroLR.xsd",
                prefix="l10n_es_verifactu",
            )
            xml_expected = etree.fromstring(PASSPORT_SPANISH_INVOICE_XML_POST)
            self.assertXmlTreeEqual(verifactu_xml, xml_expected)

    def test_create_multi_currency_invoice(self):
        with freeze_time(self.operation_date):
            self.multi_currency_invoice.action_post()
            verifactu_xml = self.env["account.edi.format"]._l10n_es_verifactu_get_xml(
                self.multi_currency_invoice
            )
            validate_xml_from_attachment(
                self.env, verifactu_xml, "soap-envelope.xsd", prefix="l10n_es_verifactu"
            )
            invoice_records_node = verifactu_xml.xpath(
                ".//sfLR:RegFactuSistemaFacturacion", namespaces=NAMESPACE_SFLR_INFO
            )[0]
            validate_xml_from_attachment(
                self.env,
                invoice_records_node,
                "SuministroLR.xsd",
                prefix="l10n_es_verifactu",
            )
            xml_expected = etree.fromstring(MULTI_CURRENCY_INVOICE_XML_POST)
            self.assertXmlTreeEqual(verifactu_xml, xml_expected)

    def test_cancel_spanish_recipient_national_fp(self):
        with freeze_time(self.operation_date):
            self.env.ref("l10n_es_edi_verifactu.edi_es_verifactu").with_context(
                l10n_es_verifactu_get_xml=True
            )._check_move_configuration(self.spanish_invoice)
            verifactu_xml = self.env["account.edi.format"]._l10n_es_verifactu_get_xml(
                self.spanish_invoice, cancel=True
            )
            validate_xml_from_attachment(
                self.env, verifactu_xml, "soap-envelope.xsd", prefix="l10n_es_verifactu"
            )
            invoice_records_node = verifactu_xml.xpath(
                ".//sfLR:RegFactuSistemaFacturacion", namespaces=NAMESPACE_SFLR_INFO
            )[0]
            validate_xml_from_attachment(
                self.env,
                invoice_records_node,
                "SuministroLR.xsd",
                prefix="l10n_es_verifactu",
            )
            xml_expected = etree.fromstring(CANCEL_SPANISH_INVOICE_XML_POST)
            self.assertXmlTreeEqual(verifactu_xml, xml_expected)

    def test_qr_url(self):
        with freeze_time(self.operation_date):
            invoice = self.spanish_invoice
            verifactu_xml = self.env["account.edi.format"]._l10n_es_verifactu_get_xml(
                invoice
            )
            invoice.update_l10n_es_edi_verifactu_xml(verifactu_xml, False)
            invoice.l10n_es_edi_verifactu_chain_index = (
                invoice.company_id.get_l10n_es_verifactu_next_chain_index()
            )
            expected_qr_url = (
                TEST_AEAT_VERIFACTU_QR_URL
                + "?nif=93074269P&numserie=INV%2F2024%2F00001&fecha=28-10-2024&importe=4840.00"
            )
            self.assertEqual(invoice.l10n_es_edi_verifactu_qr_url, expected_qr_url)
