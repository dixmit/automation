# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import tools
from odoo.tests.common import HttpCase

from odoo.addons.mail.tests.common import MockEmail

from .common import AutomationTestCase

MAIL_TEMPLATE = """Return-Path: <whatever-2a840@postmaster.twitter.com>
To: {to}
cc: {cc}
Received: by mail1.openerp.com (Postfix, from userid 10002)
    id 5DF9ABFB2A; Fri, 10 Aug 2012 16:16:39 +0200 (CEST)
From: {email_from}
Subject: {subject}
MIME-Version: 1.0
Content-Type: multipart/alternative;
    boundary="----=_Part_4200734_24778174.1344608186754"
Date: Fri, 10 Aug 2012 14:16:26 +0000
Message-ID: {msg_id}
{extra}
------=_Part_4200734_24778174.1344608186754
Content-Type: text/plain; charset=utf-8
Content-Transfer-Encoding: quoted-printable

I would gladly answer to your mass mailing !

--
Your Dear Customer
------=_Part_4200734_24778174.1344608186754
Content-Type: text/html; charset=utf-8
Content-Transfer-Encoding: quoted-printable

<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
 <head>=20
  <meta http-equiv=3D"Content-Type" content=3D"text/html; charset=3Dutf-8" />
 </head>=20
 <body style=3D"margin: 0; padding: 0; background: #ffffff;-webkit-text-size-adjust: 100%;">=20

  <p>I would gladly answer to your mass mailing !</p>

  <p>--<br/>
     Your Dear Customer
  <p>
 </body>
</html>
------=_Part_4200734_24778174.1344608186754--
"""


class TestAutomationMail(AutomationTestCase, MockEmail, HttpCase):
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

    def test_reply(self):
        """
        Now we will check the execution of scheduled activities"""
        with self.mock_mail_gateway():
            activity = self.create_mail_activity()
            child_activity = self.create_mail_activity(
                parent_id=activity.id, trigger_type="mail_reply"
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
            self.gateway_mail_reply_wrecord(
                MAIL_TEMPLATE, self.partner_01, use_in_reply_to=True
            )
            self.assertEqual("reply", record_activity.mail_status)
            self.assertTrue(record_child_activity.scheduled_date)

    def test_no_reply(self):
        """
        Now we will check the not reply validation. To remember:
        if it is not opened, the schedule date of the child task will be false
        """
        with self.mock_mail_gateway():
            activity = self.create_mail_activity()
            child_activity = self.create_mail_activity(
                parent_id=activity.id, trigger_type="mail_not_reply"
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
            self.url_open(record_activity._get_mail_tracking_url())
            self.assertEqual("open", record_activity.mail_status)
            self.assertTrue(record_child_activity.scheduled_date)
            self.gateway_mail_reply_wrecord(
                MAIL_TEMPLATE, self.partner_01, use_in_reply_to=True
            )
            self.assertEqual("reply", record_activity.mail_status)
            self.env["automation.record.activity"]._cron_automation_activities()
            self.assertEqual("rejected", record_child_activity.state)

    def test_open(self):
        """
        Now we will check the execution of scheduled activities"""
        with self.mock_mail_gateway():
            activity = self.create_mail_activity()
            child_activity = self.create_mail_activity(
                parent_id=activity.id, trigger_type="mail_open"
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
            self.url_open(record_activity._get_mail_tracking_url())
            self.assertEqual("open", record_activity.mail_status)
            self.assertTrue(record_child_activity.scheduled_date)

    def test_open_wrong_code(self):
        """
        We wan to ensure that the code is checked on the call
        """
        with self.mock_mail_gateway():
            activity = self.create_mail_activity()
            child_activity = self.create_mail_activity(
                parent_id=activity.id, trigger_type="mail_open"
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
            self.url_open(
                "/automation_oca/track/%s/INVENTED_CODE/blank.gif" % record_activity.id
            )
            self.assertEqual("sent", record_activity.mail_status)
            self.assertFalse(record_child_activity.scheduled_date)

    def test_no_open(self):
        """
        Now we will check the not open validation when it is not opened (should be executed)
        """
        with self.mock_mail_gateway():
            activity = self.create_mail_activity()
            child_activity = self.create_mail_activity(
                parent_id=activity.id, trigger_type="mail_not_open"
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
            self.assertTrue(record_child_activity.scheduled_date)
            self.env["automation.record.activity"]._cron_automation_activities()
            self.assertEqual("done", record_child_activity.state)

    def test_no_open_rejected(self):
        """
        Now we will check the not open validation when it was already opened (rejection)
        """
        with self.mock_mail_gateway():
            activity = self.create_mail_activity()
            child_activity = self.create_mail_activity(
                parent_id=activity.id, trigger_type="mail_not_open"
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
            self.assertTrue(record_child_activity.scheduled_date)
            self.url_open(record_activity._get_mail_tracking_url())
            self.assertEqual("open", record_activity.mail_status)
            self.env["automation.record.activity"]._cron_automation_activities()
            self.assertEqual("rejected", record_child_activity.state)

    def test_click(self):
        """
        Now we will check the execution of scheduled activities that should happen
        after a click
        """
        with self.mock_mail_gateway():
            activity = self.create_mail_activity()
            child_activity = self.create_mail_activity(
                parent_id=activity.id, trigger_type="mail_click"
            )
            self.configuration.domain = "[('id', '=', %s)]" % self.partner_01.id
            self.env["link.tracker"].search(
                [("url", "=", "https://www.twitter.com")]
            ).unlink()
            self.configuration.start_automation()
            self.assertEqual(0, self.configuration.click_count)
            self.env["automation.configuration"].cron_automation()
            self.env["automation.record.activity"]._cron_automation_activities()
            record_activity = self.env["automation.record.activity"].search(
                [("configuration_activity_id", "=", activity.id)]
            )
            record_child_activity = self.env["automation.record.activity"].search(
                [("configuration_activity_id", "=", child_activity.id)]
            )
            self.assertEqual("sent", record_activity.mail_status)
            self.configuration.invalidate_recordset()
            self.assertEqual(0, self.configuration.click_count)
            self.assertTrue(record_child_activity)
            self.assertFalse(record_child_activity.scheduled_date)
            self.url_open(record_activity._get_mail_tracking_url())
            self.assertEqual("open", record_activity.mail_status)
            self.configuration.invalidate_recordset()
            self.assertEqual(0, self.configuration.click_count)
            self.assertFalse(record_child_activity.scheduled_date)
            tracker = self.env["link.tracker"].search(
                [("url", "=", "https://www.twitter.com")]
            )
            self.assertTrue(tracker)
            self.url_open(
                "/r/%s/au/%s/%s"
                % (
                    tracker.code,
                    record_activity.id,
                    record_activity._get_mail_tracking_token(),
                )
            )
            self.assertEqual("open", record_activity.mail_status)
            self.assertEqual(
                1,
                self.env["link.tracker.click"].search_count(
                    [
                        ("automation_record_activity_id", "=", record_activity.id),
                        ("link_id", "=", tracker.id),
                    ]
                ),
            )
            self.assertTrue(record_child_activity.scheduled_date)

            self.configuration.invalidate_recordset()
            self.assertEqual(1, self.configuration.click_count)
            # Now we will check that a second click does not generate a second log
            self.url_open(
                "/r/%s/au/%s/%s"
                % (
                    tracker.code,
                    record_activity.id,
                    record_activity._get_mail_tracking_token(),
                )
            )
            self.assertEqual(
                1,
                self.env["link.tracker.click"].search_count(
                    [
                        ("automation_record_activity_id", "=", record_activity.id),
                        ("link_id", "=", tracker.id),
                    ]
                ),
            )
            self.configuration.invalidate_recordset()
            self.assertEqual(1, self.configuration.click_count)

    def test_click_wrong_url(self):
        """
        Now we will check that no log is processed when the clicked url is malformed.
        That happens because we add a code information on the URL.
        """
        with self.mock_mail_gateway():
            activity = self.create_mail_activity()
            child_activity = self.create_mail_activity(
                parent_id=activity.id, trigger_type="mail_click"
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
            tracker = self.env["link.tracker"].search(
                [("url", "=", "https://www.twitter.com")]
            )
            self.assertTrue(tracker)
            self.url_open(
                "/r/%s/au/%s/1234"
                % (
                    tracker.code,
                    record_activity.id,
                )
            )
            self.assertEqual("sent", record_activity.mail_status)
            self.assertFalse(record_child_activity.scheduled_date)
            # Now we check the case where the code is not found
            tracker.unlink()
            self.url_open(
                "/r/%s/au/%s/%s"
                % (
                    tracker.code,
                    record_activity.id,
                    record_activity._get_mail_tracking_token(),
                )
            )
            self.assertEqual("sent", record_activity.mail_status)
            self.assertFalse(record_child_activity.scheduled_date)

    def test_no_click(self):
        """
        Checking the not clicked validation when it is not clicked (should be executed)
        """
        with self.mock_mail_gateway():
            activity = self.create_mail_activity()
            child_activity = self.create_mail_activity(
                parent_id=activity.id, trigger_type="mail_not_clicked"
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
            self.url_open(record_activity._get_mail_tracking_url())
            self.assertEqual("open", record_activity.mail_status)
            self.assertTrue(record_child_activity.scheduled_date)
            self.env["automation.record.activity"]._cron_automation_activities()
            self.assertEqual("done", record_child_activity.state)

    def test_no_click_rejected(self):
        """
        Checking the not clicked validation when it was already clicked
        """
        with self.mock_mail_gateway():
            activity = self.create_mail_activity()
            child_activity = self.create_mail_activity(
                parent_id=activity.id, trigger_type="mail_not_clicked"
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
            self.url_open(record_activity._get_mail_tracking_url())
            self.assertEqual("open", record_activity.mail_status)
            self.assertTrue(record_child_activity.scheduled_date)
            tracker = self.env["link.tracker"].search(
                [("url", "=", "https://www.twitter.com")]
            )
            self.url_open(
                "/r/%s/au/%s/%s"
                % (
                    tracker.code,
                    record_activity.id,
                    record_activity._get_mail_tracking_token(),
                )
            )
            self.env["automation.record.activity"]._cron_automation_activities()
            self.assertEqual("rejected", record_child_activity.state)
