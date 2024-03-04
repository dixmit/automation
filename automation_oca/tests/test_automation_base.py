# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError

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
        """
        Check that the error is raised properly and stored the full error
        """
        activity = self.create_server_action(server_action_id=self.error_action.id)
        self.configuration.domain = "[('id', '=', %s)]" % self.partner_01.id
        self.configuration.start_automation()
        self.env["automation.configuration"].cron_automation()
        record = self.env["automation.record.activity"].search(
            [("configuration_activity_id", "=", activity.id)]
        )
        self.assertFalse(record.error_trace)
        self.env["automation.record.activity"]._cron_automation_activities()
        self.assertEqual(record.state, "error")
        self.assertTrue(record.error_trace)

    def test_record_resource_information(self):
        """
        Check the record computed fields of record
        """
        self.create_server_action(server_action_id=self.error_action.id)
        self.configuration.domain = "[('id', '=', %s)]" % self.partner_01.id
        self.configuration.start_automation()
        self.env["automation.configuration"].cron_automation()
        record = self.env["automation.record"].search(
            [("configuration_id", "=", self.configuration.id)]
        )
        self.assertEqual(self.partner_01.display_name, record.display_name)
        self.assertEqual(self.partner_01, record.resource_ref)
        record.model = "unexistent.model"
        self.assertFalse(record.resource_ref)

    def test_counter(self):
        """
        Check the counter function
        """
        self.create_server_action(server_action_id=self.error_action.id)
        self.configuration.domain = "[('id', '=', %s)]" % self.partner_01.id
        self.configuration.start_automation()
        self.assertEqual(0, self.configuration.record_count)
        self.env["automation.configuration"].cron_automation()
        self.configuration.invalidate_recordset()
        self.assertEqual(1, self.configuration.record_count)

    def test_start_configuration_twice_exception(self):
        """
        Check that we cannot start automation twice
        """
        self.configuration.start_automation()
        with self.assertRaises(ValidationError):
            self.configuration.start_automation()
