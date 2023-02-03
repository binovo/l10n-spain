# -*- coding: utf-8 -*-
# Copyright 2021 Binovo IT Human Project SL
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def update_general_external_ids(env):
    xmlids_to_rename = [
        ('l10n_es_extra_data.tax_group_recargo_0_625', 'l10n_es_extra_data.tax_group_recargo_0-62'),
        ('l10n_es_extra_data.fptt_recargo_0b', 'l10n_es_extra_data.fptt_recargo_0a'),
        ('l10n_es_extra_data.fptt_recargo_0b_2', 'l10n_es_extra_data.fptt_recargo_0a_2'),
        ('l10n_es_extra_data.fptt_recargo_5b', 'l10n_es_extra_data.fptt_recargo_5a'),
        ('l10n_es_extra_data.fptt_recargo_5b_2', 'l10n_es_extra_data.fptt_recargo_5a_2'),
        ('l10n_es_extra_data.fptt_recargo_buy_0b', 'l10n_es_extra_data.fptt_recargo_buy_0a'),
        ('l10n_es_extra_data.fptt_recargo_buy_0b_2', 'l10n_es_extra_data.fptt_recargo_buy_0a_2'),
        ('l10n_es_extra_data.fptt_recargo_buy_5b', 'l10n_es_extra_data.fptt_recargo_buy_5a'),
        ('l10n_es_extra_data.fptt_recargo_buy_5b_2', 'l10n_es_extra_data.fptt_recargo_buy_5a_2'),
        ('l10n_es_extra_data.account_tax_template_p_iva5_bc', 'l10n_es_extra_data.account_tax_template_p_iva5_a'),
        ('l10n_es_extra_data.account_tax_template_s_iva5b', 'l10n_es_extra_data.account_tax_template_s_iva5_a'),
        ('l10n_es_extra_data.account_tax_template_p_iva0_bc', 'l10n_es_extra_data.account_tax_template_p_iva0_a'),
        ('l10n_es_extra_data.account_tax_template_s_iva0b', 'l10n_es_extra_data.account_tax_template_s_iva0_a'),
        ('l10n_es_extra_data.account_tax_template_s_req0625', 'l10n_es_extra_data.account_tax_template_s_req062'),
        ('l10n_es_extra_data.account_tax_template_p_req0625', 'l10n_es_extra_data.account_tax_template_p_req062'),
    ]
    openupgrade.rename_xmlids(env.cr, xmlids_to_rename)


def update_company_external_ids(env):
    company_ids = env['res.company'].search([])
    xmlids_to_rename = []
    for c in company_ids:
        xmlids_to_rename += [
            ('l10n_es_extra_data.%d_account_tax_template_p_iva5_bc' % c.id, 'l10n_es_extra_data.%d_account_tax_template_p_iva5_a' % c.id),
            ('l10n_es_extra_data.%d_account_tax_template_s_iva5b' % c.id, 'l10n_es_extra_data.%d_account_tax_template_s_iva5_a' % c.id),
            ('l10n_es_extra_data.%d_account_tax_template_p_iva0_bc' % c.id, 'l10n_es_extra_data.%d_account_tax_template_p_iva0_a' % c.id),
            ('l10n_es_extra_data.%d_account_tax_template_s_iva0b' % c.id, 'l10n_es_extra_data.%d_account_tax_template_s_iva0_a' % c.id),
            ('l10n_es_extra_data.%d_account_tax_template_s_req0625' % c.id, 'l10n_es_extra_data.%d_account_tax_template_s_req062' % c.id),
            ('l10n_es_extra_data.%d_account_tax_template_p_req0625' % c.id, 'l10n_es_extra_data.%d_account_tax_template_p_req062' % c.id),
        ]
    openupgrade.rename_xmlids(env.cr, xmlids_to_rename)


def update_tax_group_name(env):
    cr = env.cr
    cr.execute(
        "SELECT res_id FROM ir_model_data "
        "WHERE module = %s AND name = %s",
        ("l10n_es_extra_data", "tax_group_recargo_0-62")
    )
    res = cr.fetchone()
    group_id = res and res[0]
    if group_id:
        cr.execute(
            "UPDATE account_tax_group SET name = %s WHERE id=%s",
            ("Recargo de Equivalencia 0.62%", group_id)
        )


@openupgrade.migrate()
def migrate(env, version):
    update_general_external_ids(env)
    update_company_external_ids(env)
    update_tax_group_name(env)
