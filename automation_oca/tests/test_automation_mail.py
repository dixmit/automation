# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

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
        self.assertTrue(self.partner_01.message_ids - messages_01)
