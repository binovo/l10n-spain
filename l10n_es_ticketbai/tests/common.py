# Copyright 2020 Binovo IT Human Project SL
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import os
from datetime import date
from lxml import etree
from urllib.request import pathname2url
from ..ticketbai.xml_schema import XMLSchema
from odoo.tests import common


@common.at_install(False)
@common.post_install(True)
class TestL10nEsTicketBAI(common.TransactionCase):

    def create_account_billing(self):
        return self.env['res.users'].with_context({'no_reset_password': True}).create({
            'name': "Accountant",
            'company_id': self.main_company.id,
            'login': 'accountuser',
            'email': 'accountuser@yourcompany.com',
            'groups_id': [(6, 0, [self.group_user.id, self.res_users_account_billing.id,
                                  self.partner_manager.id])]
        })

    def create_account_manager(self):
        return self.env['res.users'].with_context({'no_reset_password': True}).create({
            'name': 'Adviser',
            'company_id': self.main_company.id,
            'login': 'accountmanager',
            'email': 'accountmanager@yourcompany.com',
            'groups_id': [(6, 0, [self.group_user.id, self.res_users_account_manager.id,
                                  self.partner_manager.id])]
        })

    def create_draft_invoice(self, uid, fp):
        invoice = self.env['account.invoice'].sudo(uid).create({
            'partner_id': self.customer.id,
            'currency_id': self.env.ref('base.EUR').id,
            'name': 'TBAI Invoice Test',
            'account_id': self.account_receivable.id,
            'type': 'out_invoice',
            'date_invoice': date.today(),
            'tbai_date_operation': date.today(),
            'fiscal_position_id': fp.id
        })
        self.env['account.invoice.line'].sudo(uid).create({
            'invoice_id': invoice.id,
            'product_id': self.product_delivery.id,
            'quantity': 1,
            'price_unit': 100.0,
            'name': 'TBAI Invoice Line Test - delivery 1',
            'account_id': self.account_revenue.id
        })
        self.env['account.invoice.line'].sudo(uid).create({
            'invoice_id': invoice.id,
            'product_id': self.product_delivery.id,
            'quantity': 1,
            'price_unit': 100.0,
            'name': 'TBAI Invoice Line Test - delivery 2',
            'account_id': self.account_revenue.id
        })
        self.env['account.invoice.line'].sudo(uid).create({
            'invoice_id': invoice.id,
            'product_id': self.product_service.id,
            'quantity': 1,
            'discount': 10.0,
            'price_unit': 100.0,
            'name': 'TBAI Invoice Line Test - service',
            'account_id': self.account_revenue.id
        })
        for line in invoice.invoice_line_ids:
            line._onchange_product_id()
        return invoice

    def create_aeat_certificate(self):
        test_dir_path = os.path.abspath(os.path.dirname(__file__))
        p12_filepath = "%s/certs/ciudadano_act.p12" % test_dir_path
        with open(p12_filepath, 'rb') as f:
            p12_file = f.read()
        pem_filepath = "%s/certs/private_up_8mgwq.pem" % test_dir_path
        crt_filepath = "%s/certs/public_362gar7l.crt" % test_dir_path
        aeat_certificate = self.env['l10n.es.aeat.certificate'].create({
            'name': 'TicketBAI - Test certificate',
            'folder': 'TicketBAI',
            'file': p12_file,
            'private_key': pem_filepath,
            'public_key': crt_filepath,
            'company_id': self.main_company.id
        })
        aeat_certificate.action_active()
        return aeat_certificate

    def setUp(self):
        super().setUp()
        schemas_version_dirname = XMLSchema.schemas_version_dirname
        script_dirpath = os.path.abspath(os.path.dirname(__file__))
        schemas_dirpath = os.path.join(script_dirpath, '../ticketbai/schemas')
        url = pathname2url(os.path.join(schemas_dirpath, 'catalog.xml'))
        catalog_path = "file:%s" % url
        os.environ['XML_CATALOG_FILES'] = catalog_path
        # Load XSD file with XADES imports
        test_xml_customer_invoice_filepath = os.path.abspath(
            os.path.join(schemas_dirpath,
                         '%s/test_ticketBai V1-2.xsd' % schemas_version_dirname))
        self.test_xml_customer_invoice_schema_doc = etree.parse(
            test_xml_customer_invoice_filepath, parser=etree.ETCompatXMLParser())
        # Load XSD file with XADES imports
        test_xml_customer_cancellation_filepath = os.path.abspath(os.path.join(
            schemas_dirpath,
            '%s/test_Anula_ticketBai V1-2.xsd' % schemas_version_dirname))
        self.test_xml_customer_cancellation_schema_doc = etree.parse(
            test_xml_customer_cancellation_filepath, parser=etree.ETCompatXMLParser())
        self.main_company = self.env.ref('base.main_company')
        self.main_company.tbai_enabled = True
        self.main_company.tbai_tax_agency_id = self.env.ref(
            'l10n_es_ticketbai.tbai_tax_agency_gipuzkoa').id
        self.main_company.currency_id = self.env.ref('base.EUR').id
        self.main_company.partner_id.vat = 'ES12345678Z'
        self.main_company.tbai_license_key = 'TEST-LICENSE-001'
        self.main_company.tbai_device_serial_number = 'TEST-DEVICE-001'
        self.main_company.tbai_developer_id = self.env.ref(
            "l10n_es_ticketbai.res_partner_binovo").id
        aeat_certificate = self.create_aeat_certificate()
        self.main_company.tbai_certificate_id = aeat_certificate.id
        self.customer = self.env.ref("l10n_es_ticketbai.res_partner_binovo")
        self.customer_extracommunity = self.env.ref(
            'l10n_es_ticketbai.res_partner_yamaha_jp')
        self.customer_intracommunity = self.env.ref('l10n_es_ticketbai.res_partner_oca')
        self.product_delivery = self.env.ref('product.product_delivery_01')
        self.product_service = self.env.ref('product.product_product_6c')
        self.group_user = self.env.ref('base.group_user')  # Employee
        self.res_users_account_billing = self.env.ref(
            'account.group_account_invoice')  # Billing
        self.res_users_account_manager = self.env.ref(
            'account.group_account_manager')  # Billing Manager
        self.partner_manager = self.env.ref('base.group_partner_manager')
        self.account_billing = self.create_account_billing()  # Billing user
        self.account_manager = self.create_account_manager()  # Billing Manager user
        self.account_receivable = self.env['account.account'].search(
            [('user_type_id', '=',
              self.env.ref('account.data_account_type_receivable').id)], limit=1)
        self.account_revenue = self.env['account.account'].search(
            [('user_type_id', '=',
              self.env.ref('account.data_account_type_revenue').id)], limit=1)
        # Exportaciones de mercancías
        self.vat_exemption_E2 = self.env.ref('l10n_es_ticketbai.tbai_vat_exemption_E2')
        # Entregas a otro estado miembro
        self.vat_exemption_E5 = self.env.ref('l10n_es_ticketbai.tbai_vat_exemption_E5')
        # Otros
        self.vat_exemption_E6 = self.env.ref('l10n_es_ticketbai.tbai_vat_exemption_E6')
        # Bienes
        self.tax_21b = self.env['account.tax'].search(
            [('description', '=', 'S_IVA21B')])
        # Servicios
        self.tax_10s = self.env['account.tax'].search(
            [('description', '=', 'S_IVA10S')])
        # Retenciones a cuenta IRPF 15%
        self.tax_irpf_15 = self.env['account.tax'].search(
            [('description', '=', 'S_IRPF15')])
        # 1.4% Recargo Equivalencia Ventas
        self.tax_req14 = self.env['account.tax'].search(
            [('description', '=', 'S_REQ014')])
        # 5.2% Recargo Equivalencia Ventas
        self.tax_req52 = self.env['account.tax'].search(
            [('description', '=', 'S_REQ52')])
        # Bienes intracomunitarios
        self.tax_iva0_ic = self.env['account.tax'].search(
            [('description', '=', 'S_IVA0_IC')])
        # Servicios intracomunitarios
        self.tax_iva0_sp_i = self.env['account.tax'].search(
            [('description', '=', 'S_IVA0_SP_I')])
        # Bienes extracomunitarios
        self.tax_iva0_e = self.env['account.tax'].search(
            [('description', '=', 'S_IVA0_E')])
        # Servicios extracomunitarios
        self.tax_iva0_sp_e = self.env['account.tax'].search(
            [('description', '=', 'S_IVA_SP_E')])
        self.product_delivery.taxes_id = [(6, 0, [self.tax_21b.id])]
        self.product_service.taxes_id = [(6, 0, [self.tax_10s.id])]
        # 07 - Régimen especial criterio de caja
        # 05 - Régimen especial de agencias de viajes
        # 01 - Régimen general
        self.fiscal_position_national = self.env['account.fiscal.position'].create({
            'name': 'TBAI Fiscal Position - Régimen Nacional',
            'tbai_vat_regime_key': self.env.ref(
                'l10n_es_ticketbai.tbai_vat_regime_07').id,
            'tbai_vat_regime_key2': self.env.ref(
                'l10n_es_ticketbai.tbai_vat_regime_05').id,
            'tbai_vat_regime_key3': self.env.ref(
                'l10n_es_ticketbai.tbai_vat_regime_01').id
        })
        self.fiscal_position_surcharge = self.env['account.fiscal.position'].create({
            'name': 'TBAI Fiscal Position - Surcharge',
            'tbai_vat_regime_key': self.env.ref(
                'l10n_es_ticketbai.tbai_vat_regime_01').id,
            'tax_ids': [
                (0, 0, {
                    'tax_src_id': self.tax_10s.id,
                    'tax_dest_id': self.tax_10s.id
                }),
                (0, 0, {
                    'tax_src_id': self.tax_10s.id,
                    'tax_dest_id': self.tax_req14.id
                }),
                (0, 0, {
                    'tax_src_id': self.tax_21b.id,
                    'tax_dest_id': self.tax_21b.id
                }),
                (0, 0, {
                    'tax_src_id': self.tax_21b.id,
                    'tax_dest_id': self.tax_req52.id
                })
            ]
        })
        self.fiscal_position_irpf15 = self.env['account.fiscal.position'].create({
            'name': 'TBAI Fiscal Position - Withholding Tax 15%',
            'tbai_vat_regime_key': self.env.ref(
                'l10n_es_ticketbai.tbai_vat_regime_01').id,
            'tax_ids': [
                (0, 0, {
                    'tax_src_id': self.tax_21b.id,
                    'tax_dest_id': self.tax_21b.id
                }),
                (0, 0, {
                    'tax_src_id': self.tax_21b.id,
                    'tax_dest_id': self.tax_irpf_15.id
                })
            ]
        })
        self.fiscal_position_ic = self.env['account.fiscal.position'].create({
            'name': 'TBAI Fiscal Position - European Union (Intracommunity Operations)',
            'tbai_vat_regime_key': self.env.ref(
                'l10n_es_ticketbai.tbai_vat_regime_01').id,
            'tbai_vat_exemption_ids': [
                (0, 0, {
                    'tax_id': self.tax_iva0_ic.id,
                    'tbai_vat_exemption_key': self.vat_exemption_E5.id
                }),
                (0, 0, {
                    'tax_id': self.tax_iva0_sp_i.id,
                    'tbai_vat_exemption_key': self.vat_exemption_E5.id
                })
            ],
            'tax_ids': [
                (0, 0, {
                    'tax_src_id': self.tax_21b.id,
                    'tax_dest_id': self.tax_iva0_ic.id
                }),
                (0, 0, {
                    'tax_src_id': self.tax_10s.id,
                    'tax_dest_id': self.tax_iva0_sp_i.id
                })
            ]
        })
        self.fiscal_position_e = self.env['account.fiscal.position'].create({
            'name': 'TBAI Fiscal Position - Exports (Extracommunity Operations)',
            'tbai_vat_regime_key': self.env.ref(
                'l10n_es_ticketbai.tbai_vat_regime_02').id,
            'tbai_vat_exemption_ids': [
                (0, 0, {
                    'tax_id': self.tax_iva0_e.id,
                    'tbai_vat_exemption_key': self.vat_exemption_E2.id
                }),
                (0, 0, {
                    'tax_id': self.tax_iva0_sp_e.id,
                    'tbai_vat_exemption_key': self.vat_exemption_E6.id
                })
            ],
            'tax_ids': [
                (0, 0, {
                    'tax_src_id': self.tax_21b.id,
                    'tax_dest_id': self.tax_iva0_e.id
                }),
                (0, 0, {
                    'tax_src_id': self.tax_10s.id,
                    'tax_dest_id': self.tax_iva0_sp_e.id
                })
            ]
        })