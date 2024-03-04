# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestAutomation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.action = cls.env["ir.actions.server"].create(
            {
                "name": "Demo action",
                "state": "code",
                "model_id": cls.env.ref("base.model_res_partner").id,
                "code": "records.write({'comment': env.context.get('key_value')})",
            }
        )
        cls.partner_01 = cls.env["res.partner"].create(
            {"name": "Demo partner", "comment": "Demo"}
        )
        cls.partner_02 = cls.env["res.partner"].create(
            {"name": "Demo partner 2", "comment": "Demo"}
        )
        cls.configuration = cls.env["automation.configuration"].create(
            {
                "name": "Test configuration",
                "model_id": cls.env.ref("base.model_res_partner").id,
            }
        )

    @classmethod
    def create_server_action(cls, parent_id=False, **kwargs):
        return cls.env["automation.configuration.activity"].create(
            {
                "name": "Demo activity",
                "parent_id": parent_id,
                "configuration_id": cls.configuration.id,
                "activity_type": "action",
                "server_action_id": cls.action.id,
                "trigger_type": "activity" if parent_id else "start",
                **kwargs,
            }
        )

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

    def test_activity_execution(self):
        """
        We will check the execution of the tasks and that we cannot execute them again
        """
        activity = self.create_server_action()
        self.configuration.domain = "[('id', '=', %s)]" % self.partner_01.id
        self.configuration.start_automation()
        self.env["automation.configuration"].cron_automation()
        self.assertTrue(self.partner_01.comment)
        self.assertTrue(self.partner_02.comment)
        self.env["automation.record.activity"]._cron_automation_activities()
        self.assertFalse(self.partner_01.comment)
        self.assertTrue(self.partner_02.comment)
        record_activity = self.env["automation.record.activity"].search(
            [("configuration_activity_id", "=", activity.id)]
        )
        self.assertEqual(1, len(record_activity))
        self.assertEqual("done", record_activity.state)
        self.partner_01.comment = "My comment"
        # We check that the action is not executed again
        record_activity.run()
        self.assertTrue(self.partner_01.comment)

    def test_child_execution_filters(self):
        """
        We will create a task that executes two more tasks filtered with and extra task
        The child tasks should only be created after the first one is finished.
        Also, if one is aborted, the subsuquent tasks will not be created.
        TASK 1 ---> TASK 1_1 (only for partner 1) --> TASK 1_1_1
               ---> TASK 1_2 (only for partner 2) --> TASK 1_2_1

        In this case, the task 1_1_1 will only be generated for partner 1 and task 1_2_1
        for partner 2
        """
        self.configuration.domain = "[('id', 'in', [%s, %s])]" % (
            self.partner_01.id,
            self.partner_02.id,
        )

        activity_1 = self.create_server_action()
        activity_1_1 = self.create_server_action(
            parent_id=activity_1.id, domain="[('id', '=', %s)]" % self.partner_01.id
        )
        activity_1_2 = self.create_server_action(
            parent_id=activity_1.id, domain="[('id', '=', %s)]" % self.partner_02.id
        )
        activity_1_1_1 = self.create_server_action(parent_id=activity_1_1.id)
        activity_1_2_1 = self.create_server_action(parent_id=activity_1_2.id)
        self.configuration.start_automation()
        self.env["automation.configuration"].cron_automation()
        self.assertEqual(
            0,
            self.env["automation.record.activity"].search_count(
                [
                    (
                        "configuration_activity_id",
                        "in",
                        (
                            activity_1_1
                            | activity_1_2
                            | activity_1_1_1
                            | activity_1_2_1
                        ).ids,
                    )
                ]
            ),
        )
        self.assertTrue(self.partner_01.comment)
        self.assertTrue(self.partner_02.comment)
        self.env["automation.record.activity"]._cron_automation_activities()
        self.assertFalse(self.partner_01.comment)
        self.assertFalse(self.partner_02.comment)
        self.assertEqual(
            1,
            self.env["automation.record.activity"].search_count(
                [
                    ("configuration_activity_id", "=", activity_1_1.id),
                    ("record_id.res_id", "=", self.partner_01.id),
                ]
            ),
        )
        self.assertEqual(
            1,
            self.env["automation.record.activity"].search_count(
                [
                    ("configuration_activity_id", "=", activity_1_2.id),
                    ("record_id.res_id", "=", self.partner_01.id),
                ]
            ),
        )
        self.assertEqual(
            1,
            self.env["automation.record.activity"].search_count(
                [
                    ("configuration_activity_id", "=", activity_1_1.id),
                    ("record_id.res_id", "=", self.partner_02.id),
                ]
            ),
        )
        self.assertEqual(
            1,
            self.env["automation.record.activity"].search_count(
                [
                    ("configuration_activity_id", "=", activity_1_2.id),
                    ("record_id.res_id", "=", self.partner_02.id),
                ]
            ),
        )
        self.assertEqual(
            0,
            self.env["automation.record.activity"].search_count(
                [
                    (
                        "configuration_activity_id",
                        "in",
                        (activity_1_1_1 | activity_1_2_1).ids,
                    )
                ]
            ),
        )
        self.env["automation.record.activity"]._cron_automation_activities()
        self.assertEqual(
            1,
            self.env["automation.record.activity"].search_count(
                [
                    ("configuration_activity_id", "=", activity_1_1.id),
                    ("record_id.res_id", "=", self.partner_01.id),
                    ("state", "=", "done"),
                ]
            ),
        )
        self.assertEqual(
            1,
            self.env["automation.record.activity"].search_count(
                [
                    ("configuration_activity_id", "=", activity_1_2.id),
                    ("record_id.res_id", "=", self.partner_01.id),
                    ("state", "=", "rejected"),
                ]
            ),
        )
        self.assertEqual(
            1,
            self.env["automation.record.activity"].search_count(
                [
                    ("configuration_activity_id", "=", activity_1_1.id),
                    ("record_id.res_id", "=", self.partner_02.id),
                    ("state", "=", "rejected"),
                ]
            ),
        )
        self.assertEqual(
            1,
            self.env["automation.record.activity"].search_count(
                [
                    ("configuration_activity_id", "=", activity_1_2.id),
                    ("record_id.res_id", "=", self.partner_02.id),
                    ("state", "=", "done"),
                ]
            ),
        )
        self.assertEqual(
            1,
            self.env["automation.record.activity"].search_count(
                [
                    ("configuration_activity_id", "=", activity_1_1_1.id),
                    ("record_id.res_id", "=", self.partner_01.id),
                ]
            ),
        )
        self.assertEqual(
            0,
            self.env["automation.record.activity"].search_count(
                [
                    ("configuration_activity_id", "=", activity_1_2_1.id),
                    ("record_id.res_id", "=", self.partner_01.id),
                ]
            ),
        )
        self.assertEqual(
            0,
            self.env["automation.record.activity"].search_count(
                [
                    ("configuration_activity_id", "=", activity_1_1_1.id),
                    ("record_id.res_id", "=", self.partner_02.id),
                ]
            ),
        )
        self.assertEqual(
            1,
            self.env["automation.record.activity"].search_count(
                [
                    ("configuration_activity_id", "=", activity_1_2_1.id),
                    ("record_id.res_id", "=", self.partner_02.id),
                ]
            ),
        )
