# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AutomationRecord(models.Model):

    _name = "automation.record"
    _description = "Automation Record"

    name = fields.Char(compute="_compute_name")
    state = fields.Selection(
        [("run", "Running"), ("done", "Done")], compute="_compute_state", store=True
    )
    configuration_id = fields.Many2one(
        "automation.configuration", required=True, readonly=True
    )
    model = fields.Char(index=True, required=False, readonly=True)
    resource_ref = fields.Reference(
        selection="_selection_target_model",
        compute="_compute_resource_ref",
        readonly=True,
    )
    res_id = fields.Many2oneReference(
        string="Record",
        index=True,
        required=False,
        readonly=True,
        model_field="model",
        copy=False,
    )
    automation_activity_ids = fields.One2many(
        "automation.record.activity", inverse_name="record_id", readonly=True
    )

    @api.model
    def _selection_target_model(self):
        return [
            (model.model, model.name)
            for model in self.env["ir.model"]
            .sudo()
            .search([("is_mail_thread", "=", True)])
        ]

    @api.depends("automation_activity_ids.state")
    def _compute_state(self):
        for record in self:
            record.state = (
                "run"
                if record.automation_activity_ids.filtered(
                    lambda r: r.state == "scheduled"
                )
                else "done"
            )

    @api.depends("model", "res_id")
    def _compute_resource_ref(self):
        for record in self:
            if record.model and record.model in self.env:
                record.resource_ref = "%s,%s" % (record.model, record.res_id or 0)
            else:
                record.resource_ref = None

    @api.depends("res_id", "model")
    def _compute_name(self):
        for record in self:
            record.name = self.env[record.model].browse(record.res_id).display_name
