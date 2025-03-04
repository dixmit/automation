# Copyright 2025 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AutomationFlowchart(models.Model):

    _name = "automation.flowchart"
    _description = "Automation Flowchart"

    name = fields.Char(compute="_compute_name", store=True)

    automation_configuration_id = fields.Many2one(
        "automation.configuration", string="Automation Configuration", required=True
    )

    @api.depends("automation_configuration_id")
    def _compute_name(self):
        for record in self:
            if record.automation_configuration_id:
                record.name = record.automation_configuration_id.name + " Flowchart"

    def action_open_flowchart(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "action_automation_flowchart",
            "params": {"flowchart_id": self.id, "model": self._name},
        }


class AutomationFlowchartItem(models.Model):
    _name = "automation.flowchart.item"
    _description = "Automation Flowchart Item"
