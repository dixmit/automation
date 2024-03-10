# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from collections import defaultdict

import babel.dates
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools import get_lang
from odoo.tools.safe_eval import safe_eval


class AutomationConfigurationActivity(models.Model):

    _name = "automation.configuration.activity"
    _description = "Automation Activity"
    _order = "trigger_interval_hours ASC"

    name = fields.Char(required=True)
    configuration_id = fields.Many2one(
        "automation.configuration", required=True, auto_join=True
    )
    domain = fields.Char(
        required=True, default="[]", help="Filter to apply specifically"
    )
    applied_domain = fields.Char(
        compute="_compute_applied_domain",
        recursive=True,
    )
    parent_id = fields.Many2one("automation.configuration.activity", ondelete="cascade")
    model_id = fields.Many2one(related="configuration_id.model_id")
    model = fields.Char(related="model_id.model")
    child_ids = fields.One2many(
        "automation.configuration.activity", inverse_name="parent_id"
    )
    activity_type = fields.Selection(
        [("mail", "Mail"), ("action", "Server Action")], required=True, default="mail"
    )
    trigger_interval_hours = fields.Integer(
        compute="_compute_trigger_interval_hours", store=True
    )
    trigger_interval = fields.Integer()
    trigger_interval_type = fields.Selection(
        [("hours", "Hours"), ("days", "Days")], required=True, default="hours"
    )
    expiry = fields.Boolean()
    expiry_interval = fields.Integer()
    expiry_interval_type = fields.Selection(
        [("hours", "Hours"), ("days", "Days")], required=True, default="hours"
    )
    trigger_type = fields.Selection(
        [
            ("start", "start of workflow"),
            ("activity", "execution of another activity"),
            ("mail_open", "Mail opened"),
            ("mail_not_open", "Mail not opened"),
            ("mail_reply", "Mail replied"),
            ("mail_not_reply", "Mail not replied"),
            ("mail_click", "Mail clicked"),
            ("mail_not_clicked", "Mail not clicked"),
            ("mail_bounce", "Mail bounced"),
        ],
        required=True,
        default="start",
    )
    trigger_activity_id = fields.Many2one(
        "automation.configuration.activity",
        domain="[('configuration_id', '=', configuration_id)]",
    )
    mail_author_id = fields.Many2one(
        "res.partner", required=True, default=lambda r: r.env.user.id
    )
    mail_template_id = fields.Many2one(
        "mail.template", domain="[('model_id', '=', model_id)]"
    )
    server_action_id = fields.Many2one(
        "ir.actions.server", domain="[('model_id', '=', model_id)]"
    )
    parent_position = fields.Integer(
        compute="_compute_parent_position", recursive=True, store=True
    )
    graph_data = fields.Json(compute="_compute_graph_data")
    graph_done = fields.Integer(compute="_compute_total_graph_data")
    graph_error = fields.Integer(compute="_compute_total_graph_data")

    @api.depends()
    def _compute_graph_data(self):
        total = self.env["automation.record.activity"].read_group(
            [
                ("configuration_activity_id", "in", self.ids),
                ("processed_on", ">=", fields.Date.today() + relativedelta(days=-14)),
            ],
            ["configuration_activity_id"],
            ["configuration_activity_id", "processed_on:day"],
            lazy=False,
        )
        done = self.env["automation.record.activity"].read_group(
            [
                ("configuration_activity_id", "in", self.ids),
                ("processed_on", ">=", fields.Date.today() + relativedelta(days=-14)),
                ("state", "=", "done"),
            ],
            ["configuration_activity_id"],
            ["configuration_activity_id", "processed_on:day"],
            lazy=False,
        )
        now = fields.Datetime.now()
        date_map = {
            babel.dates.format_datetime(
                now + relativedelta(days=i - 14),
                format="dd MMM yyy",
                tzinfo=self._context.get("tz", None),
                locale=get_lang(self.env).code,
            ): 0
            for i in range(0, 15)
        }
        result = defaultdict(
            lambda: {"done": date_map.copy(), "error": date_map.copy()}
        )
        for line in total:
            result[line["configuration_activity_id"][0]]["error"][
                line["processed_on:day"]
            ] += line["__count"]
        for line in done:
            result[line["configuration_activity_id"][0]]["done"][
                line["processed_on:day"]
            ] += line["__count"]
            result[line["configuration_activity_id"][0]]["error"][
                line["processed_on:day"]
            ] -= line["__count"]
        for record in self:
            graph_info = dict(result[record.id])
            record.graph_data = {
                "error": [
                    {"x": key[:-5], "y": value, "name": key}
                    for (key, value) in graph_info["error"].items()
                ],
                "done": [
                    {"x": key[:-5], "y": value, "name": key}
                    for (key, value) in graph_info["done"].items()
                ],
            }

    @api.depends()
    def _compute_total_graph_data(self):
        for record in self:
            record.graph_done = self.env["automation.record.activity"].search_count(
                [
                    ("configuration_activity_id", "in", self.ids),
                    ("state", "=", "done"),
                ]
            )
            record.graph_error = self.env["automation.record.activity"].search_count(
                [
                    ("configuration_activity_id", "in", self.ids),
                    ("state", "in", ["expired", "rejected", "error", "cancel"]),
                ]
            )

    @api.depends("trigger_interval", "trigger_interval_type")
    def _compute_trigger_interval_hours(self):
        for record in self:
            record.trigger_interval_hours = record._get_trigger_interval_hours()

    def _get_trigger_interval_hours(self):
        if self.trigger_interval_type == "days":
            return self.trigger_interval * 24
        return self.trigger_interval

    @api.depends("parent_id", "parent_id.parent_position")
    def _compute_parent_position(self):
        for record in self:
            record.parent_position = (
                (record.parent_id.parent_position + 1) if record.parent_id else 0
            )

    @api.depends(
        "domain", "configuration_id.domain", "parent_id", "parent_id.applied_domain"
    )
    def _compute_applied_domain(self):
        for record in self:
            record.applied_domain = expression.AND(
                [
                    safe_eval(record.domain),
                    safe_eval(
                        (record.parent_id and record.parent_id.applied_domain)
                        or record.configuration_id.domain
                    ),
                ]
            )

    def _get_record_activity_scheduled_date(self):
        if self.trigger_type in [
            "mail_open",
            "mail_bounce",
            "mail_click",
            "mail_not_clicked",
            "mail_reply",
            "mail_not_reply",
        ]:
            return False
        return fields.Datetime.now() + relativedelta(
            **{self.trigger_interval_type: self.trigger_interval}
        )

    def _get_expiry_date(self):
        if not self.expiry:
            return False
        return fields.Datetime.now() + relativedelta(
            **{self.expiry_interval_type: self.expiry_interval}
        )

    def _create_record_activity_vals(self, record, **kwargs):
        return {
            "configuration_activity_id": self.id,
            "expiry_date": self._get_expiry_date(),
            "scheduled_date": self._get_record_activity_scheduled_date(),
            **kwargs,
        }
