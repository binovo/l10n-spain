import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo8-addons-oca-l10n-spain",
    description="Meta package for oca-l10n-spain Odoo addons",
    version=version,
    install_requires=[
        'odoo8-addon-account_balance_reporting',
        'odoo8-addon-account_balance_reporting_xls',
        'odoo8-addon-account_refund_original',
        'odoo8-addon-l10n_es',
        'odoo8-addon-l10n_es_account_asset',
        'odoo8-addon-l10n_es_account_balance_report',
        'odoo8-addon-l10n_es_account_bank_statement_import_n43',
        'odoo8-addon-l10n_es_account_banking_sepa_fsdd',
        'odoo8-addon-l10n_es_account_financial_report',
        'odoo8-addon-l10n_es_account_financial_report_xlsx',
        'odoo8-addon-l10n_es_account_invoice_sequence',
        'odoo8-addon-l10n_es_aeat',
        'odoo8-addon-l10n_es_aeat_mod111',
        'odoo8-addon-l10n_es_aeat_mod115',
        'odoo8-addon-l10n_es_aeat_mod123',
        'odoo8-addon-l10n_es_aeat_mod130',
        'odoo8-addon-l10n_es_aeat_mod216',
        'odoo8-addon-l10n_es_aeat_mod296',
        'odoo8-addon-l10n_es_aeat_mod303',
        'odoo8-addon-l10n_es_aeat_mod340',
        'odoo8-addon-l10n_es_aeat_mod340_cash_basis',
        'odoo8-addon-l10n_es_aeat_mod340_type0',
        'odoo8-addon-l10n_es_aeat_mod347',
        'odoo8-addon-l10n_es_aeat_mod349',
        'odoo8-addon-l10n_es_aeat_sii',
        'odoo8-addon-l10n_es_aeat_vat_prorrate',
        'odoo8-addon-l10n_es_aeat_vat_prorrate_asset',
        'odoo8-addon-l10n_es_cnae',
        'odoo8-addon-l10n_es_crm_lead_trade_name',
        'odoo8-addon-l10n_es_dua',
        'odoo8-addon-l10n_es_dua_sii',
        'odoo8-addon-l10n_es_fiscal_year_closing',
        'odoo8-addon-l10n_es_irnr',
        'odoo8-addon-l10n_es_location_nuts',
        'odoo8-addon-l10n_es_partner',
        'odoo8-addon-l10n_es_partner_mercantil',
        'odoo8-addon-l10n_es_payment_order',
        'odoo8-addon-l10n_es_payment_order_confirminet',
        'odoo8-addon-l10n_es_payment_order_confirming_bankia',
        'odoo8-addon-l10n_es_payment_order_confirming_popular',
        'odoo8-addon-l10n_es_payment_order_confirming_sabadell',
        'odoo8-addon-l10n_es_pos',
        'odoo8-addon-l10n_es_subcontractor_certificate',
        'odoo8-addon-l10n_es_toponyms',
        'odoo8-addon-l10n_es_vat_book',
        'odoo8-addon-payment_redsys',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
