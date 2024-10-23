# -*- coding: utf-8 -*-
# Copyright 2024 Binovo IT Human Project SL
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, fields
from odoo.osv.expression import NEGATIVE_TERM_OPERATORS


class AccountEdiDocument(models.Model):
    _inherit = "account.edi.document"

    verifactu_state = fields.Selection(
        [
            ("to_send", "To Send"),
            ("sent", "Sent"),
            ("to_cancel", "To Cancel"),
            ("cancelled", "Cancelled"),
            ("error", "Error"),
        ],
        compute="_compute_verifactu_state",
        search="_search_verifactu_state",
        readonly=True,
    )

    def _compute_verifactu_state(self):
        for rec in self:
            is_error = (
                True
                if rec.state in ["to_send", "to_cancel"]
                and rec.blocking_level == "error"
                else False
            )
            rec.verifactu_state = "error" if is_error else rec.state

    def _search_verifactu_state(self, operator, value):
        if value == "error":
            docs = self.search(
                [
                    ("state", "in", ["to_send", "to_cancel"]),
                    ("blocking_level", "=", "error"),
                ]
            )
        else:
            domain = [("state", "=", value)]
            if value in ["to_send", "to_cancel"]:
                domain += [("blocking_level", "!=", "error")]
            docs = self.search(domain)
        new_op = "not in" if operator in NEGATIVE_TERM_OPERATORS else "in"
        return [("id", new_op, docs.ids)]

    # -------------------------------------------------------------------------
    # EDI OVERRIDDEN METHODS
    # -------------------------------------------------------------------------

    def _prepare_jobs(self):
        # TODO filter jobs to send according to ControlFlujoEnvios parameters
        jobs = super()._prepare_jobs()
        return jobs
