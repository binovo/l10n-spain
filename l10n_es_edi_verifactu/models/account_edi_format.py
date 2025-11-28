# -*- coding: utf-8 -*-
# Copyright 2024 Binovo IT Human Project SL
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import copy
import json
import os
import requests
import tempfile
from base64 import b64encode
from datetime import datetime
from markupsafe import Markup
from lxml import etree
from odoo import models, api, _
from odoo.exceptions import ValidationError, UserError
from ..lib.verifactu_xmlgen import verifactu_xmlgen
from ..lib.verifactu_xmlgen import OPERATION_CREATE, OPERATION_CANCEL

VERIFACTU_XML_ENVELOPE = """
<soapenv:Envelope
    xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:sfLR="https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroLR.xsd"
    xmlns:sf="https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroInformacion.xsd">
    <soapenv:Header/>
    <soapenv:Body>
        <sfLR:RegFactuSistemaFacturacion>
            <sfLR:Cabecera>
                <sf:ObligadoEmision>
                    <sf:NombreRazon/>
                    <sf:NIF/>
                </sf:ObligadoEmision>
            </sfLR:Cabecera>
            <sfLR:RegistroFactura/>
        </sfLR:RegFactuSistemaFacturacion>
    </soapenv:Body>
</soapenv:Envelope>
""".encode(
    "utf-8"
)

TEST_AEAT_VERIFACTU_SERVICE_URL = (
    "https://prewww1.aeat.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP"
)

TEST_AEAT_VERIFACTU_QR_URL = "https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR"

NAMESPACE_TIK_INFO = {
    "tik": "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroInformacion.xsd"
}

NAMESPACE_SFLR_INFO = {
    "sfLR": "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroLR.xsd"
}

NAMESPACE_SF_INFO = {
    "sf": "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroInformacion.xsd"
}

NAMESPACE_TIK_RESPONSE = {
    "tikR": "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/RespuestaSuministro.xsd"
}

NAMESPACE_SOAP = {"env": "http://schemas.xmlsoap.org/soap/envelope/"}


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    def _l10n_es_edi_verifactu_content(self, invoice):
        cancel = invoice.edi_state in ("to_cancel", "cancelled")
        xml_tree = self._l10n_es_verifactu_get_xml(invoice, cancel)
        xml_str = etree.tostring(xml_tree)
        return xml_str

    def _l10n_es_edi_verifactu_post_invoice(self, invoice):
        if self.code != "es_verifactu":
            return super()._post_invoice_edi(invoice)

        # Call the web service and get response
        res = self._l10n_es_verifactu_post_to_web_service(invoice)
        if res[invoice].get("response"):
            test_suffix = (
                _("(test mode)") if invoice.company_id.l10n_es_edi_test_env else ""
            )
            invoice.with_context(no_new_invoice=True).message_post(
                body=_(
                    "<pre>Verifactu: posted emission XML response %(test_suffix)s</pre>"
                )
                % {"test_suffix": test_suffix},
                attachments=[
                    (
                        invoice.name + "_verifactu_post_response.xml",
                        etree.tostring(res[invoice].get("response"), encoding="UTF-8"),
                        {"mimetype": "application/xml"},
                    )
                ],
            )
        # Create attachment, post and save as EDI DOC
        attachment = self.env["ir.attachment"].create(
            {
                "name": invoice.name + "_verifactu_post.xml",
                "datas": invoice.l10n_es_edi_verifactu_xml,
                "mimetype": "application/xml",
                "res_id": invoice.id,
                "res_model": "account.move",
            }
        )
        test_suffix = (
            _("(test mode)") if invoice.company_id.l10n_es_edi_test_env else ""
        )
        invoice.with_context(no_new_invoice=True).message_post(
            body=Markup(
                _("<pre>Verifactu: posted emission XML {test_suffix}\n{message}</pre>")
            ).format(
                test_suffix=test_suffix, message=res[invoice].get("message", "XXX")
            ),
            attachment_ids=[attachment.id],
        )
        if res[invoice].get("success", False):
            invoice.with_context(no_new_invoice=True).message_post(
                body="Verifactu URL: <a href='%s' target='_blank'> %s </a>"
                % (
                    invoice.l10n_es_edi_verifactu_qr_url,
                    invoice.l10n_es_edi_verifactu_qr_url,
                )
            )
        res[invoice]["attachment"] = attachment
        return res

    def _l10n_es_edi_verifactu_cancel_invoice(self, invoice):
        # EXTENDS account_edi
        if self.code != "es_verifactu":
            return super()._cancel_invoice_edi(invoice)

        # Generate the XML values.
        verifactu_cancel_xml = self._l10n_es_verifactu_get_xml(invoice, cancel=True)

        # Store the XML as attachment to ensure it is never lost (even in case of timeout error)
        invoice.update_l10n_es_edi_verifactu_xml(verifactu_cancel_xml, True)

        # Call the web service and get response
        res = self._l10n_es_verifactu_post_to_web_service(invoice, cancel=True)
        if res[invoice].get("response"):
            test_suffix = (
                _("(test mode)") if invoice.company_id.l10n_es_edi_test_env else ""
            )
            invoice.with_context(no_new_invoice=True).message_post(
                body=_(
                    "<pre>Verifactu: posted cancellation XML response %(test_suffix)s</pre>"
                )
                % {"test_suffix": test_suffix},
                attachments=[
                    (
                        invoice.name + "_verifactu_cancel_post_response.xml",
                        etree.tostring(res[invoice].get("response"), encoding="UTF-8"),
                        {"mimetype": "application/xml"},
                    )
                ],
            )
        # Create attachment, post and save as EDI DOC
        attachment = self.env["ir.attachment"].create(
            {
                "name": invoice.name + "_verifactu_cancel_post.xml",
                "datas": invoice.l10n_es_edi_verifactu_cancel_xml,
                "mimetype": "application/xml",
                "res_id": invoice.id,
                "res_model": "account.move",
            }
        )
        test_suffix = (
            _("(test mode)") if invoice.company_id.l10n_es_edi_test_env else ""
        )
        invoice.with_context(no_new_invoice=True).message_post(
            body=Markup(
                _(
                    "<pre>Verifactu: posted cancellation XML {test_suffix}\n{message}</pre>"
                )
            ).format(
                test_suffix=test_suffix, message=res[invoice].get("message", "XXX")
            ),
            attachment_ids=[attachment.id],
        )
        res[invoice]["attachment"] = attachment
        return res

    def _l10n_es_verifactu_get_xml(self, invoice, cancel=False):
        """l10n_es_edi_verifactu: generates the XML"""
        # If previously generated XML reuse it
        xml_root_node = invoice.get_l10n_es_edi_verifactu_xml(cancel)
        if xml_root_node is not None:
            return xml_root_node
        # Otherwise, generate a new XML
        self._ensure_verifactu_supported_invoice(invoice)
        errors = self._ensure_verifactu_software_settings(
            invoice
        ) + self._ensure_verifactu_invoice_data(invoice)
        if errors:
            raise UserError(
                _("Invalid invoice configuration:\n\n%s") % "\n".join(errors)
            )
        invoice_records_xml = self.cmd_get_verifactu_xml(invoice, cancel=cancel)
        root_records = etree.fromstring(invoice_records_xml)
        xml_root_node = etree.fromstring(VERIFACTU_XML_ENVELOPE)
        issuer_name_node = xml_root_node.xpath(
            ".//sf:NombreRazon", namespaces=NAMESPACE_SF_INFO
        )[0]
        issuer_name_node.text = invoice.company_id.name[:120]
        issuer_vat_node = xml_root_node.xpath(
            ".//sf:NIF", namespaces=NAMESPACE_SF_INFO
        )[0]
        issuer_vat_node.text = (
            invoice.company_id.vat[2:]
            if invoice.company_id.vat.startswith("ES")
            else invoice.company_id.vat
        )
        records_node = xml_root_node.xpath(
            ".//sfLR:RegistroFactura", namespaces=NAMESPACE_SFLR_INFO
        )[0]
        for child_node in root_records:
            records_node.append(copy.deepcopy(child_node))
        return xml_root_node

    def _l10n_es_verifactu_aeat_service_url(self, invoice):
        if invoice.company_id.l10n_es_edi_test_env:
            return TEST_AEAT_VERIFACTU_SERVICE_URL
        else:
            # TODO post to verifactu production systems, not available yet
            raise NotImplementedError()

    def _l10n_es_verifactu_aeat_qr_url(self, invoice):
        if invoice.company_id.l10n_es_edi_test_env:
            return TEST_AEAT_VERIFACTU_QR_URL
        else:
            # TODO post to verifactu production systems, not available yet
            raise NotImplementedError()

    def _l10n_es_verifactu_post_to_web_service(self, invoice, cancel=False):
        try:
            session = requests.Session()
            company_pkcs12 = invoice.company_id.l10n_es_edi_certificate_id
            cert_content, key_content, _certificate = (
                company_pkcs12._decode_certificate()
            )
            with tempfile.NamedTemporaryFile(
                mode="wb"
            ) as cert_file, tempfile.NamedTemporaryFile(mode="wb") as key_file:
                cert_file.write(cert_content)
                key_file.write(key_content)
                cert_file.flush()
                key_file.flush()
                session.cert = (cert_file.name, key_file.name)
                headers = {"Content-Type": "text/xml; charset=utf-8"}
                data = etree.tostring(
                    invoice.get_l10n_es_edi_verifactu_xml(cancel=cancel),
                    encoding="UTF-8",
                )
                response = session.request(
                    "post",
                    self._l10n_es_verifactu_aeat_service_url(invoice),
                    data=data,
                    headers=headers,
                )
                success, message, response_xml = (
                    self._l10n_es_verifactu_process_post_response(response)
                )
        except (ValueError, requests.exceptions.RequestException) as e:
            return {
                invoice: {
                    "error": str(e),
                    "blocking_level": "warning",
                    "response": None,
                }
            }
        if success:
            return {
                invoice: {
                    "success": True,
                    "message": message,
                    "response": response_xml,
                }
            }
        else:
            return {
                invoice: {
                    "error": message,
                    "blocking_level": "error",
                    "response": response_xml,
                }
            }

    def _l10n_es_verifactu_process_post_response(self, response):
        try:
            response_xml = etree.fromstring(response.content)
        except etree.XMLSyntaxError as e:
            return False, str(e) + "\n" + str(response.content or ""), None

        # --- Check for SOAP Fault in Response ---
        # This must be done first, as a fault response does not contain the tikR elements.
        fault_string_node = response_xml.xpath(
            ".//env:Fault/faultstring", namespaces=NAMESPACE_SOAP
        )
        if fault_string_node:
            error_message = fault_string_node[0].text
            return False, _("AEAT Error: ") + error_message, response_xml

        # --- Standard tikR Response (RespuestaSuministro.xsd) ---
        already_received = False
        error_code = False
        error_message = False
        sent_state = response_xml.xpath(
            ".//tikR:EstadoEnvio", namespaces=NAMESPACE_TIK_RESPONSE
        )
        sent_state_txt = sent_state[0].text if sent_state else ""
        message = _("Sent state: ") + sent_state_txt + "\n"
        csv_code_node = response_xml.xpath(
            ".//tikR:CSV", namespaces=NAMESPACE_TIK_RESPONSE
        )
        if csv_code_node:
            message += "CSV: " + csv_code_node[0].text + "\n"
        for xml_res_node in response_xml.xpath(
            ".//tikR:RespuestaLinea", namespaces=NAMESPACE_TIK_RESPONSE
        ):
            record_state = response_xml.xpath(
                ".//tikR:EstadoRegistro", namespaces=NAMESPACE_TIK_RESPONSE
            )
            duplicated_record_state = response_xml.xpath(
                ".//tik:EstadoRegistroDuplicado", namespaces=NAMESPACE_TIK_INFO
            )
            if duplicated_record_state:
                message += (
                    _("Duplicated record state: ")
                    + duplicated_record_state[0].text
                    + "\n"
                )
            else:
                message += _("Record state: ") + record_state[0].text + "\n"
            error_code_node = xml_res_node.xpath(
                ".//tikR:CodigoErrorRegistro", namespaces=NAMESPACE_TIK_RESPONSE
            )
            if error_code_node:
                error_code = error_code_node[0].text
            error_message_node = xml_res_node.xpath(
                ".//tikR:DescripcionErrorRegistro", namespaces=NAMESPACE_TIK_RESPONSE
            )
            if error_message_node:
                error_message = error_message_node[0].text
            if error_code and error_message:
                message += error_code + ": " + error_message + "\n"
            if error_code and error_code in ("3000", "3001"):
                already_received = True
        response_success = (
            sent_state_txt in ("Correcto", "ParcialmenteCorrecto") or already_received
        )
        return response_success, message, response_xml

    @staticmethod
    def _get_verifactu_issuer(invoice):
        return {
            "irsId": invoice.company_id.vat[2:]
            if invoice.company_id.vat.startswith("ES")
            else invoice.company_id.vat,
            "name": invoice.company_id.name,
        }

    @staticmethod
    def _get_verifactu_invoice_id(invoice, cancel=False):
        issued_time = (
            datetime.now().isoformat()
            if not cancel
            else invoice.get_verifactu_issued_time_from_xml()
        )
        if cancel:
            xml_issued_time = invoice.get_verifactu_issued_time_from_xml()
            if xml_issued_time:
                issued_time = xml_issued_time
        return {
            "number": invoice.name[:60],
            "issuedTime": issued_time,
        }

    @staticmethod
    def _get_verifactu_recipient(partner_id, partner_info):
        recipient = {
            "name": partner_id.name[:120],
            "country": partner_id.country_id.code,
        }
        if partner_id.is_spanish_nif():
            recipient["irsId"] = partner_info.get("NIF")
        else:
            recipient_id = (
                partner_info.get("NIF")
                if partner_id.is_spanish()
                else partner_info.get("IDOtro").get("ID")
            )
            recipient["id"] = recipient_id
            recipient["idType"] = (
                partner_id.l10n_es_edi_verifactu_partner_id_type
                or partner_info.get("IDOtro").get("IDType")
            )
        return recipient

    @staticmethod
    def _get_verifactu_description(invoice):
        return {
            "text": invoice.invoice_origin or "/",
            "operationDate": invoice.invoice_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    @staticmethod
    def _get_verifactu_invoice_type(invoice):
        simplified_partner = invoice.env.ref("l10n_es_edi_sii.partner_simplified")
        is_simplified = invoice.partner_id == simplified_partner
        if invoice.move_type == "out_invoice":
            return "F2" if is_simplified else "F1"
        elif invoice.move_type == "out_refund":
            return "R5" if is_simplified else "R1"
        else:
            return ""

    @staticmethod
    def _get_verifactu_credit_note(invoice):
        return {
            "style": "I",
            "ids": [
                AccountEdiFormat._get_verifactu_invoice_id(invoice.reversed_entry_id)
            ],
        }

    @staticmethod
    def _get_verifactu_vat_lines(vat_breakdown):
        subject_lines = []
        no_subject_lines = []
        subject_breakdown = vat_breakdown.get("Sujeta", False)
        no_subject_breakdown = vat_breakdown.get("NoSujeta", False)
        tax_amount = 0
        if subject_breakdown:
            if subject_breakdown.get("NoExenta", False):
                tax_details = (
                    subject_breakdown.get("NoExenta")
                    .get("DesgloseIVA")
                    .get("DetalleIVA")
                )
                for tax_detail in tax_details:
                    subject_lines.append(
                        {
                            "base": tax_detail.get("BaseImponible"),
                            "rate": tax_detail.get("TipoImpositivo"),
                            "amount": tax_detail.get("CuotaRepercutida"),
                            "vatOperation": subject_breakdown.get("NoExenta").get(
                                "TipoNoExenta"
                            ),
                            "vatKey": "01",
                        }
                    )
                    tax_amount += tax_detail.get("CuotaRepercutida")
            if subject_breakdown.get("Exenta", False):
                tax_details = subject_breakdown.get("Exenta").get("DetalleExenta")
                for tax_detail in tax_details:
                    exempt_reason = tax_detail.get("CausaExencion")
                    subject_lines.append(
                        {
                            "base": tax_detail.get("BaseImponible"),
                            "rate": 0,
                            "vatOperation": exempt_reason,
                            "vatKey": "01" if exempt_reason != "E2" else "02",
                        }
                    )
        if no_subject_breakdown:
            not_subject_rl = no_subject_breakdown.get(
                "ImporteTAIReglasLocalizacion", False
            )
            not_subject_ot = no_subject_breakdown.get(
                "ImportePorArticulos7_14_Otros", False
            )
            if not_subject_rl:
                no_subject_lines.append(
                    {
                        "base": not_subject_rl,
                        "rate": 0,
                        # Spanish customer and tax is not subjet because of reglas de localización,
                        # so it should be a sale to Canarias, Ceuta or Melilla 08 vat key
                        "vatKey": "08",
                        "vatOperation": "N2",
                    }
                )
            if not_subject_ot:
                no_subject_lines.append(
                    {
                        "base": not_subject_ot,
                        "rate": 0,
                        "vatKey": "01",
                        "vatOperation": "N1",
                    }
                )
        return tax_amount, subject_lines + no_subject_lines

    @staticmethod
    def _get_verifactu_previous_id(previous_invoice):
        previous_issuer_id = previous_invoice.get_verifactu_issuer_vat_from_xml() or ""
        xml_issued_time = previous_invoice.get_verifactu_issued_time_from_xml()
        previous_hash = previous_invoice.get_verifactu_hash_from_xml() or ""
        return {
            "number": previous_invoice.name,
            "issuerIrsId": previous_issuer_id,
            "issuedTime": xml_issued_time if xml_issued_time else "",
            "hash": previous_hash,
        }

    def _attach_verifactu_xmlgen_json_input(self, attach_datas, invoice, cancel=False):
        attach_name = (
            invoice.name + "_verifactu_xmlgen.json"
            if not cancel
            else invoice.name + "_cancel_verifactu_xmlgen.json"
        )
        self.env["ir.attachment"].search(
            [("name", "=", attach_name), ("res_model", "=", "account.move")]
        ).unlink()
        attachment = self.env["ir.attachment"].create(
            {
                "name": attach_name,
                "datas": b64encode(json.dumps(attach_datas, indent=4).encode("UTF-8")),
                "mimetype": "application/json",
                "res_id": invoice.id,
                "res_model": "account.move",
            }
        )
        invoice.with_context(no_new_invoice=True).message_post(
            body="verifactu-xml json:", attachment_ids=[attachment.id]
        )

    @api.model
    def verifactu_xmlgen_prepare_json(self, invoice, cancel=False, attach=False):
        if invoice and not cancel:
            json_input = {
                "invoice": {
                    "issuer": self._get_verifactu_issuer(invoice),
                    "recipient": self._get_verifactu_recipient(
                        invoice.commercial_partner_id,
                        self._l10n_es_edi_get_partner_info(
                            invoice.commercial_partner_id
                        ),
                    ),
                    "id": self._get_verifactu_invoice_id(invoice, cancel),
                    "description": self._get_verifactu_description(invoice),
                    "type": self._get_verifactu_invoice_type(invoice),
                }
            }
            if invoice.move_type == "out_refund":
                json_input["invoice"]["creditNote"] = self._get_verifactu_credit_note(
                    invoice
                )
            tax_details_info_vals = self._l10n_es_edi_get_invoices_tax_details_info(
                invoice
            )
            if tax_details_info_vals:
                sign = -1 if invoice.move_type == "out_refund" else 1
                total_amount = round(
                    sign
                    * (
                        tax_details_info_vals["tax_details"]["base_amount"]
                        + tax_details_info_vals["tax_details"]["tax_amount"]
                        - tax_details_info_vals["tax_amount_retention"]
                    ),
                    2,
                )
                tax_amount, vat_lines = self._get_verifactu_vat_lines(
                    tax_details_info_vals.get("tax_details_info")
                )
                json_input["invoice"]["vatLines"] = vat_lines
                json_input["invoice"]["total"] = total_amount
                json_input["invoice"]["amount"] = tax_amount
            previous_invoice = (
                invoice.company_id.get_l10n_es_verifactu_last_posted_invoice()
            )
            if previous_invoice:
                json_input["previousId"] = self._get_verifactu_previous_id(
                    previous_invoice
                )
            if attach:
                self._attach_verifactu_xmlgen_json_input(json_input, invoice)
            return json_input
        elif invoice and cancel:
            json_input = {
                "invoice": {
                    "issuer": self._get_verifactu_issuer(invoice),
                    "id": self._get_verifactu_invoice_id(invoice, cancel),
                }
            }
            previous_invoice = (
                invoice.company_id.get_l10n_es_verifactu_last_posted_invoice()
            )
            if previous_invoice:
                json_input["previousId"] = self._get_verifactu_previous_id(
                    previous_invoice
                )
            if attach:
                self._attach_verifactu_xmlgen_json_input(json_input, invoice)
            return json_input
        else:
            raise ValidationError(_("Verifactu: invoice needed."))

    @api.model
    def cmd_get_verifactu_xml(self, invoice, cancel=False):
        json_input = self.verifactu_xmlgen_prepare_json(
            invoice, cancel=cancel, attach=True
        )
        process = verifactu_xmlgen(
            OPERATION_CANCEL if cancel else OPERATION_CREATE,
            json.dumps(json_input),
            self.env,
            invoice.company_id,
        )
        if process.returncode != 0:
            err_msgs = (
                process.stderr.decode("utf-8").split("\n") if process.stderr else []
            )
            validation_error = err_msgs[0] if len(err_msgs) > 0 else ""
            if len(err_msgs) > 2:
                code = err_msgs[1]
                validation_error = "Verifactu verifactu-xmlgen: [%s] %s" % (
                    code,
                    validation_error,
                )
                validation_error += "\n" + json.dumps(json_input, indent=4)
            raise ValidationError(validation_error)
        json_result = json.loads(process.stdout)
        return base64.b64decode(json_result["verifactuXml"])

    # -------------------------------------------------------------------------
    # EDI OVERRIDDEN METHODS
    # -------------------------------------------------------------------------

    def _get_move_applicability(self, move):
        self.ensure_one()
        if self.code != "es_verifactu":
            return super()._get_move_applicability(move)
        if move.l10n_es_edi_verifactu_is_required:
            return {
                "post": self._l10n_es_edi_verifactu_post_invoice,
                "cancel": self._l10n_es_edi_verifactu_cancel_invoice,
                # TODO post_batching is needed in case of t waiting time or n number invoices to wait in the response
                # 'post_batching': lambda invoice: (invoice.move_type, invoice.l10n_es_edi_csv),
                "edi_content": self._l10n_es_edi_verifactu_content,
            }

    @staticmethod
    def _ensure_verifactu_software_settings(invoice):
        errors = []
        license_data = invoice.company_id.get_l10n_es_verifactu_license_dict()
        developer_id = license_data.get("developer_id", False)
        software_id = license_data.get("software_id", False)
        software_name = license_data.get("software_name", False)
        software_number = license_data.get("software_number", False)
        software_version = license_data.get("software_version", False)
        software_settings = (
            developer_id
            and software_id
            and software_name
            and software_number
            and software_version
        )
        if not software_settings:
            errors.append(
                _("Verifactu: please configure all software data in general settings.")
            )
        return errors

    @staticmethod
    def _ensure_verifactu_invoice_data(invoice):
        errors = []
        if not invoice.company_id.vat:
            errors.append(
                _(
                    "VAT number is missing on company %s",
                    invoice.company_id.display_name,
                )
            )
        if not invoice.partner_id.country_id:
            errors.append(
                _("Country is missing on partner %s", invoice.partner_id.name)
            )
        if not invoice.partner_id.vat:
            errors.append(
                _("VAT number is missing on partner %s", invoice.partner_id.name)
            )
        if (
            not invoice.partner_id.is_from_eu()
            and not invoice.partner_id.l10n_es_edi_verifactu_partner_id_type
        ):
            raise ValidationError(_("ID Type is mandatory for non-community partners."))
        if not invoice.fiscal_position_id:
            errors.append(
                _(
                    "Fiscal position is required in invoice, you can set on partner %s",
                    invoice.partner_id.name,
                )
            )
        return errors

    @staticmethod
    def _ensure_verifactu_supported_invoice(invoice):
        # TODO Not supported invoices that actually we should support
        # 3. Simplified invoices
        simplified_partner = invoice.env.ref("l10n_es_edi_sii.partner_simplified")
        is_simplified = invoice.partner_id == simplified_partner
        if is_simplified:
            raise ValidationError(
                _("Verifactu: simplified invoices are not supported.")
            )
        # 4. Non supported tax
        supported_taxes = ["exento", "sujeto", "no_sujeto", "no_sujeto_loc", "ignore"]
        if any(
            tax
            for tax in invoice.invoice_line_ids.tax_ids.filtered(
                lambda tax: tax.l10n_es_type not in supported_taxes
            )
        ):
            raise ValidationError(_("Verifactu: not supported invoice taxes."))
        return True

    def _check_move_configuration(self, invoice):
        errors = super()._check_move_configuration(invoice)
        if self.code != "es_verifactu" or invoice.country_code != "ES":
            return errors
        errors += self._ensure_verifactu_software_settings(invoice)
        errors += self._ensure_verifactu_invoice_data(invoice)
        if not errors and self.env.context.get("l10n_es_verifactu_get_xml", False):
            self._ensure_verifactu_supported_invoice(invoice)
            verifactu_xml = self._l10n_es_verifactu_get_xml(invoice)
            invoice.update_l10n_es_edi_verifactu_xml(verifactu_xml, False)
            # Assign unique 'chain index' from dedicated sequence
            if not invoice.l10n_es_edi_verifactu_chain_index:
                invoice.l10n_es_edi_verifactu_chain_index = (
                    invoice.company_id.get_l10n_es_verifactu_next_chain_index()
                )
        return errors

    def _needs_web_services(self):
        return self.code == "es_verifactu" or super()._needs_web_services()

    def _is_enabled_by_default_on_journal(self, journal):
        """Disable SII by default on a new journal when verifactu is installed"""
        if self.code != "es_sii":
            return super()._is_enabled_by_default_on_journal(journal)
        return False

    def _is_compatible_with_journal(self, journal):
        if self.code != "es_verifactu":
            return super()._is_compatible_with_journal(journal)
        return journal.country_code == "ES" and journal.type == "sale"
