# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class MailThread(models.AbstractModel):

    _inherit = "mail.thread"

    @api.model
    def _routing_handle_bounce(self, email_message, message_dict):
        """We want to mark the bounced email"""
        result = super(MailThread, self)._routing_handle_bounce(
            email_message, message_dict
        )
        bounced_msg_id = message_dict.get("bounced_msg_id")
        if bounced_msg_id:
            self.env["automation.record.activity"].search(
                [("message_id", "=", bounced_msg_id)]
            )._set_mail_bounced()
        return result
