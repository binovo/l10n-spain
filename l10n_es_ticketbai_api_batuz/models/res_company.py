# Copyright 2021 Binovo IT Human Project SL
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from collections import OrderedDict
from odoo import models, fields
from .lroe_operation import LROEModelEnum


class ResCompany(models.Model):
    _inherit = 'res.company'

    lroe_model = fields.Selection([(LROEModelEnum.model_pj_240.value, 'LROE PJ 240'),
                                   (LROEModelEnum.model_pf_140.value, 'LROE PF 140')],
                                  string="LROE Model", required=True, default=LROEModelEnum.model_pj_240.value)
