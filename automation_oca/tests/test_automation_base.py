# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from .common import AutomationTestCase


class TestAutomationBase(AutomationTestCase):
    def test_no_cron_no_start(self):
        """
        We want to check that the system only generates on validated configurations
        """
        self.env["automation.configuration"].cron_automation()
        self.assertEqual(
            0,
            self.env["automation.record"].search_count(
                [("configuration_id", "=", self.configuration.id)]
            ),
        )
        self.configuration.run_automation()
        self.assertEqual(
            0,
            self.env["automation.record"].search_count(
                [("configuration_id", "=", self.configuration.id)]
            ),
        )

    def test_cron_no_duplicates(self):
        """
        We want to check that the records are generated only once, not twice
        """
        self.create_server_action()
        self.configuration.start_automation()
        self.env["automation.configuration"].cron_automation()
        record = self.env["automation.record"].search(
            [
                ("configuration_id", "=", self.configuration.id),
                ("res_id", "=", self.partner_01.id),
            ]
        )
        self.assertEqual(
            1,
            self.env["automation.record"].search_count(
                [
                    ("configuration_id", "=", self.configuration.id),
                    ("res_id", "=", self.partner_01.id),
                ]
            ),
        )
        self.assertEqual(
            1,
            self.env["automation.record"].search_count(
                [
                    ("configuration_id", "=", self.configuration.id),
                    ("res_id", "=", self.partner_02.id),
                ]
            ),
        )

        self.env["automation.configuration"].cron_automation()
        self.assertEqual(
            1,
            self.env["automation.record"].search_count(
                [
                    ("configuration_id", "=", self.configuration.id),
                    ("res_id", "=", self.partner_01.id),
                ]
            ),
        )
        self.assertEqual(
            1,
            self.env["automation.record"].search_count(
                [
                    ("configuration_id", "=", self.configuration.id),
                    ("res_id", "=", self.partner_02.id),
                ]
            ),
        )
        record = self.env["automation.record"].search(
            [
                ("configuration_id", "=", self.configuration.id),
                ("res_id", "=", self.partner_01.id),
            ]
        )
        self.assertEqual(
            1,
            self.env["automation.record.activity"].search_count(
                [("record_id", "=", record.id)]
            ),
        )

    def test_filter(self):
        """
        We want to see that the records are only generated for
        the records that fulfill the domain
        """
        self.create_server_action()
        self.configuration.domain = "[('id', '=', %s)]" % self.partner_01.id
        self.configuration.start_automation()
        self.env["automation.configuration"].cron_automation()
        self.assertEqual(
            1,
            self.env["automation.record"].search_count(
                [
                    ("configuration_id", "=", self.configuration.id),
                    ("res_id", "=", self.partner_01.id),
                ]
            ),
        )
        self.assertEqual(
            0,
            self.env["automation.record"].search_count(
                [
                    ("configuration_id", "=", self.configuration.id),
                    ("res_id", "=", self.partner_02.id),
                ]
            ),
        )

    def test_exception(self):
        activity = self.create_server_action(server_action_id=self.error_action.id)
        self.configuration.domain = "[('id', '=', %s)]" % self.partner_01.id
        self.configuration.start_automation()
        self.env["automation.configuration"].cron_automation()
        self.env["automation.record.activity"]._cron_automation_activities()
        record = self.env["automation.record.activity"].search(
            [("configuration_activity_id", "=", activity.id)]
        )
        self.assertEqual(record.state, "error")
