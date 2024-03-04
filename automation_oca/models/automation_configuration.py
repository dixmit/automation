# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.query import _generate_table_alias
from odoo.tools.safe_eval import safe_eval


class AutomationConfiguration(models.Model):

    _name = "automation.configuration"
    _description = "Automation Configuration"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company")
    domain = fields.Char(required=True, default="[]", help="Filter to apply")
    model_id = fields.Many2one(
        "ir.model",
        domain=[("is_mail_thread", "=", True)],
        required=True,
        ondelete="cascade",
        help="Model where the configuration is applied",
    )
    model = fields.Char(related="model_id.model")
    field_id = fields.Many2one(
        "ir.model.fields",
        domain="[('model_id', '=', model_id), "
        "('ttype', 'in', ['char', 'selection', 'integer', 'text', 'many2one'])]",
        help="Used to avoid duplicates",
    )  # TODO: filter by this field??
    state = fields.Selection(
        [("draft", "Draft"), ("run", "Running"), ("stop", "Stopped")],
        default="draft",
        required=True,
    )
    automation_activity_ids = fields.One2many(
        "automation.configuration.activity", inverse_name="configuration_id"
    )
    automation_direct_activity_ids = fields.One2many(
        "automation.configuration.activity",
        inverse_name="configuration_id",
        domain=[("parent_id", "=", False)],
    )
    record_count = fields.Integer(compute="_compute_record_count")

    @api.depends()
    def _compute_record_count(self):
        data = self.env["automation.record"].read_group(
            [("configuration_id", "in", self.ids)], [], ["configuration_id"], lazy=False
        )
        mapped_data = {d["configuration_id"][0]: d["__count"] for d in data}
        for record in self:
            record.record_count = mapped_data.get(record.id, 0)

    def start_automation(self):
        self.ensure_one()
        if self.state != "draft":
            raise ValidationError(_("State must be in draft in order to start"))
        self.state = "run"

    def cron_automation(self):
        for record in self.search([("state", "=", "run")]):
            record.run_automation()

    def run_automation(self):
        self.ensure_one()
        if self.state != "run":
            return
        domain = safe_eval(self.domain)
        Record = self.env[self.model_id.model]
        query = Record._where_calc(domain)
        query.left_join(
            query._tables[Record._table],
            "id",
            "automation_record",
            "res_id",
            "automation_record",
            "{rhs}.model = %s AND {rhs}.configuration_id = %s",
            (Record._name, self.id),
        )
        query.add_where(
            "{}.id is NULL".format(
                _generate_table_alias(query._tables[Record._table], "automation_record")
            )
        )
        query_str, params = query.select()
        self.env.cr.execute(query_str, params)
        records = Record.browse([r[0] for r in self.env.cr.fetchall()])
        for record in records:
            self._create_record(record)

    def _create_record(self, record):
        return self.env["automation.record"].create(self._create_record_vals(record))

    def _create_record_vals(self, record):
        return {
            "res_id": record.id,
            "model": record._name,
            "configuration_id": self.id,
            "automation_activity_ids": [
                (0, 0, activity._create_record_activity_vals(record))
                for activity in self.automation_direct_activity_ids
            ],
        }
