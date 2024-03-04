# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailMail(models.Model):

    _inherit = "mail.mail"

    automation_record_activity_id = fields.Many2one("automation.record.activity")

    @api.model_create_multi
    def create(self, values_list):
        records = super().create(values_list)
        for record in records.filtered("automation_record_activity_id"):
            record.automation_record_activity_id.message_id = record.message_id
        return records
