# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import tools

from .common import AutomationTestCase


class TestAutomationMail(AutomationTestCase):
    def test_activity_execution(self):
        """
        We will check the execution of the tasks and that we cannot execute them again
        """
        activity = self.create_mail_activity()
        self.configuration.domain = "[('id', '=', %s)]" % self.partner_01.id
        self.configuration.start_automation()
        self.env["automation.configuration"].cron_automation()
        messages_01 = self.partner_01.message_ids
        self.env["automation.record.activity"]._cron_automation_activities()
        record_activity = self.env["automation.record.activity"].search(
            [("configuration_activity_id", "=", activity.id)]
        )
        self.assertEqual(1, len(record_activity))
        self.assertEqual("done", record_activity.state)
        self.assertEqual("sent", record_activity.mail_status)
        self.assertTrue(self.partner_01.message_ids - messages_01)

    def test_bounce(self):
        """
        Now we will check the execution of scheduled activities"""
        activity = self.create_mail_activity()
        child_activity = self.create_mail_activity(
            parent_id=activity.id, trigger_type="mail_bounce"
        )
        self.configuration.domain = "[('id', '=', %s)]" % self.partner_01.id
        self.configuration.start_automation()
        self.env["automation.configuration"].cron_automation()
        self.env["automation.record.activity"]._cron_automation_activities()
        record_activity = self.env["automation.record.activity"].search(
            [("configuration_activity_id", "=", activity.id)]
        )
        record_child_activity = self.env["automation.record.activity"].search(
            [("configuration_activity_id", "=", child_activity.id)]
        )
        self.assertEqual("sent", record_activity.mail_status)
        self.assertTrue(record_child_activity)
        self.assertFalse(record_child_activity.scheduled_date)
        parsed_bounce_values = {
            "email_from": "some.email@external.example.com",
            "to": "bounce@test.example.com",
            "message_id": tools.generate_tracking_message_id("MailTest"),
            "bounced_partner": self.env["res.partner"].sudo(),
            "bounced_message": self.env["mail.message"].sudo(),
            "bounced_email": "",
            "bounced_msg_id": [record_activity.message_id],
        }
        self.env["mail.thread"]._routing_handle_bounce(False, parsed_bounce_values)
        self.assertEqual("bounce", record_activity.mail_status)
        self.assertTrue(record_child_activity.scheduled_date)
