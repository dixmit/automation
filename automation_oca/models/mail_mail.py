# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, tools


class MailMail(models.Model):

    _inherit = "mail.mail"

    automation_record_activity_id = fields.Many2one("automation.record.activity")

    @api.model_create_multi
    def create(self, values_list):
        records = super().create(values_list)
        for record in records.filtered("automation_record_activity_id"):
            record.automation_record_activity_id.message_id = record.message_id
        return records

    def _send_prepare_body(self):
        body = super()._send_prepare_body()
        if self.automation_record_activity_id:
            tracking_url = self.automation_record_activity_id._get_mail_tracking_url()
            body = tools.append_content_to_html(
                body,
                '<img src="%s"/>' % tracking_url,
                plaintext=False,
            )
        return body
