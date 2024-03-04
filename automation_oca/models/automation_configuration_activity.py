# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval


class AutomationConfigurationActivity(models.Model):

    _name = "automation.configuration.activity"
    _description = "Automation Activity"

    name = fields.Char(required=True)
    configuration_id = fields.Many2one(
        "automation.configuration", required=True, auto_join=True
    )
    domain = fields.Char(
        required=True, default="[]", help="Filter to apply specifically"
    )
    applied_domain = fields.Char(
        compute="_compute_applied_domain",
    )
    parent_id = fields.Many2one("automation.configuration.activity")
    model_id = fields.Many2one(related="configuration_id.model_id")
    model = fields.Char(related="model_id.model")
    child_ids = fields.One2many(
        "automation.configuration.activity", inverse_name="parent_id"
    )
    activity_type = fields.Selection(
        [("mail", "Mail"), ("action", "Server Action")], required=True, default="mail"
    )
    trigger_interval = fields.Integer()
    trigger_interval_type = fields.Selection(
        [("hours", "Hours"), ("days", "Days")], required=True, default="hours"
    )
    trigger_type = fields.Selection(
        [
            ("start", "start of workflow"),
            ("activity", "execution of another activity"),
            # ("mail_open", "Mail opened"),
            # ("mail_not_open", "Mail not opened"),
            # ("mail_click", "Mail clicked"),
            # ("mail_not_clicked", "Mail not clicked"),
            # ("mail_bounce", "Mail bounced"),
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

    @api.depends("domain", "configuration_id.domain", "parent_id.applied_domain")
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

    def _create_record_activity_vals(self, record, **kwargs):
        return {
            "configuration_activity_id": self.id,
            "scheduled_date": fields.Datetime.now()
            + relativedelta(**{self.trigger_interval_type: self.trigger_interval}),
            **kwargs,
        }
