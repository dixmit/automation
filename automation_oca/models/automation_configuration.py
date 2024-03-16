# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class AutomationConfiguration(models.Model):

    _name = "automation.configuration"
    _description = "Automation Configuration"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company")
    domain = fields.Char(
        required=True, default="[]", help="Filter to apply", compute="_compute_domain"
    )
    editable_domain = fields.Char(required=True, default="[]", help="Filter to apply")
    model_id = fields.Many2one(
        "ir.model",
        domain=[("is_mail_thread", "=", True)],
        required=True,
        ondelete="cascade",
        help="Model where the configuration is applied",
    )
    filter_id = fields.Many2one("automation.filter")
    filter_domain = fields.Binary(compute="_compute_filter_domain")
    model = fields.Char(related="model_id.model")
    field_id = fields.Many2one(
        "ir.model.fields",
        domain="[('model_id', '=', model_id), "
        "('ttype', 'in', ['char', 'selection', 'integer', 'text', 'many2one'])]",
        help="Used to avoid duplicates",
    )
    state = fields.Selection(
        [("draft", "Draft"), ("run", "Running"), ("stop", "Stopped")],
        default="draft",
        required=True,
        group_expand="_group_expand_states",
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
    record_done_count = fields.Integer(compute="_compute_record_count")
    record_run_count = fields.Integer(compute="_compute_record_count")
    activity_mail_count = fields.Integer(compute="_compute_activity_count")
    activity_action_count = fields.Integer(compute="_compute_activity_count")
    click_count = fields.Integer(compute="_compute_click_count")

    @api.depends("filter_id.domain", "filter_id", "editable_domain")
    def _compute_domain(self):
        for record in self:
            record.domain = (
                record.filter_id and record.filter_id.domain
            ) or record.editable_domain

    @api.depends()
    def _compute_click_count(self):
        data = self.env["link.tracker.click"].read_group(
            [("automation_configuration_id", "in", self.ids)],
            [],
            ["automation_configuration_id"],
            lazy=False,
        )
        mapped_data = {d["automation_configuration_id"][0]: d["__count"] for d in data}
        for record in self:
            record.click_count = mapped_data.get(record.id, 0)

    @api.depends()
    def _compute_activity_count(self):
        data = self.env["automation.record.activity"].read_group(
            [("configuration_id", "in", self.ids), ("state", "=", "done")],
            [],
            ["configuration_id", "activity_type"],
            lazy=False,
        )
        mapped_data = defaultdict(lambda: {})
        for d in data:
            mapped_data[d["configuration_id"][0]][d["activity_type"]] = d["__count"]
        for record in self:
            record.activity_mail_count = mapped_data[record.id].get("mail", 0)
            record.activity_action_count = mapped_data[record.id].get("action", 0)

    @api.depends()
    def _compute_record_count(self):
        data = self.env["automation.record"].read_group(
            [("configuration_id", "in", self.ids)],
            [],
            ["configuration_id", "state"],
            lazy=False,
        )
        mapped_data = defaultdict(lambda: {})
        for d in data:
            mapped_data[d["configuration_id"][0]][d["state"]] = d["__count"]
        for record in self:
            record.record_done_count = mapped_data[record.id].get("done", 0)
            record.record_run_count = mapped_data[record.id].get("run", 0)
            record.record_count = sum(mapped_data[record.id].values())

    @api.depends("model_id")
    def _compute_filter_domain(self):
        for record in self:
            record.filter_domain = (
                [] if not record.model_id else [("model_id", "=", record.model_id.id)]
            )

    @api.onchange("filter_id")
    def _onchange_filter(self):
        self.model_id = self.filter_id.model_id

    def start_automation(self):
        self.ensure_one()
        if self.state != "draft":
            raise ValidationError(_("State must be in draft in order to start"))
        self.state = "run"

    def stop_automation(self):
        self.ensure_one()
        self.state = "stop"

    def back_to_draft(self):
        self.ensure_one()
        self.state = "draft"

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
        alias = query.left_join(
            query._tables[Record._table],
            "id",
            "automation_record",
            "res_id",
            "automation_record",
            "{rhs}.model = %s AND {rhs}.configuration_id = %s",
            (Record._name, self.id),
        )
        query.add_where("{}.id is NULL".format(alias))
        if self.field_id:
            linked_tab = query.left_join(
                query._tables[Record._table],
                self.field_id.name,
                Record._table,
                self.field_id.name,
                "linked",
            )
            alias2 = query.left_join(
                linked_tab,
                "id",
                "automation_record",
                "res_id",
                "automation_record_linked",
                "{rhs}.model = %s AND {rhs}.configuration_id = %s",
                (Record._name, self.id),
            )
            query.add_where("{}.id is NULL".format(alias2))
            from_clause, where_clause, params = query.get_sql()
            query_str = "SELECT {} FROM {} WHERE {}{}{}{} GROUP BY {}".format(
                ", ".join([f'MIN("{next(iter(query._tables))}".id) as id']),
                from_clause,
                where_clause or "TRUE",
                (" ORDER BY %s" % self.order) if query.order else "",
                (" LIMIT %d" % self.limit) if query.limit else "",
                (" OFFSET %d" % self.offset) if query.offset else "",
                "%s.%s" % (query._tables[Record._table], self.field_id.name),
            )
        else:
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

    def _group_expand_states(self, states, domain, order):
        return [key for key, _val in self._fields["state"].selection]

    def save_filter(self):
        self.ensure_one()
        self.filter_id = self.env["automation.filter"].create(
            {
                "name": self.name,
                "domain": self.editable_domain,
                "model_id": self.model_id.id,
            }
        )
