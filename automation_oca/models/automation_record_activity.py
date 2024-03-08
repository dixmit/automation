# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import threading
import traceback
from io import StringIO

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class AutomationRecordActivity(models.Model):
    _name = "automation.record.activity"
    _description = "Activities done on the record"
    _order = "scheduled_date DESC"

    name = fields.Char(related="configuration_activity_id.name")
    record_id = fields.Many2one("automation.record", required=True, ondelete="cascade")
    configuration_activity_id = fields.Many2one(
        "automation.configuration.activity", required=True
    )
    activity_type = fields.Selection(related="configuration_activity_id.activity_type")
    scheduled_date = fields.Datetime(readonly=True)
    processed_on = fields.Datetime(readonly=True)
    parent_id = fields.Many2one("automation.record.activity", readonly=True)
    child_ids = fields.One2many("automation.record.activity", inverse_name="parent_id")
    trigger_type = fields.Selection(related="configuration_activity_id.trigger_type")
    state = fields.Selection(
        [
            ("scheduled", "Scheduled"),
            ("done", "Done"),
            ("rejected", "Rejected"),
            ("error", "Error"),
            ("cancel", "Cancelled"),
        ],
        default="scheduled",
        readonly=True,
    )
    error_trace = fields.Text(readonly=True)
    parent_position = fields.Integer(
        compute="_compute_parent_position", recursive=True, store=True
    )

    # Mailing fields
    message_id = fields.Char(readonly=True)
    mail_status = fields.Selection(
        [
            ("sent", "Sent"),
            ("open", "Opened"),
            ("reply", "Replied"),
            ("bounce", "Bounced"),
            ("error", "Exception"),
            ("cancel", "Canceled"),
        ]
    )

    @api.depends("parent_id", "parent_id.parent_position")
    def _compute_parent_position(self):
        for record in self:
            record.parent_position = (
                (record.parent_id.parent_position + 1) if record.parent_id else 0
            )

    def run(self):
        self.ensure_one()
        if self.state != "scheduled":
            return
        if (
            self.record_id.resource_ref is None
            or not self.record_id.resource_ref.filtered_domain(
                safe_eval(self.configuration_activity_id.applied_domain)
            )
        ):
            self.write({"state": "rejected"})
            return
        try:
            getattr(self, "_run_%s" % self.configuration_activity_id.activity_type)()
            self.write({"state": "done", "processed_on": fields.Datetime.now()})
        except Exception:
            buff = StringIO()
            traceback.print_exc(file=buff)
            traceback_txt = buff.getvalue()
            self.write({"state": "error", "error_trace": traceback_txt})

    def _fill_childs(self, **kwargs):
        self.record_id.write(
            {
                "automation_activity_ids": [
                    (
                        0,
                        0,
                        activity._create_record_activity_vals(
                            self.record_id.resource_ref, parent_id=self.id, **kwargs
                        ),
                    )
                    for activity in self.configuration_activity_id.child_ids
                ]
            }
        )

    def _run_mail(self):
        author_id = self.configuration_activity_id.mail_author_id.id
        composer_values = {
            "author_id": author_id,
            "record_name": False,
            "model": self.record_id.model,
            "composition_mode": "mass_mail",
            "template_id": self.configuration_activity_id.mail_template_id.id,
            "automation_record_activity_id": self.id,
        }
        res_ids = [self.record_id.res_id]
        composer = (
            self.env["mail.compose.message"]
            .with_context(active_ids=res_ids)
            .create(composer_values)
        )
        update_values = composer._onchange_template_id(
            self.configuration_activity_id.mail_template_id.id,
            "mass_mail",
            self.record_id.model,
            self.record_id.res_id,
        )["value"]
        composer.write(update_values)
        extra_context = self._run_mail_context()
        composer = composer.with_context(active_ids=res_ids, **extra_context)
        # auto-commit except in testing mode
        auto_commit = not getattr(threading.current_thread(), "testing", False)
        composer._action_send_mail(auto_commit=auto_commit)
        self.mail_status = "sent"
        self._fill_childs()
        return

    def _run_mail_context(self):
        return {}

    def _run_action(self):
        self.configuration_activity_id.server_action_id.with_context(
            active_model=self.record_id.model,
            active_ids=[self.record_id.res_id],
        ).run()
        self._fill_childs()

    def _cron_automation_activities(self):
        for activity in self.search(
            [
                ("state", "=", "scheduled"),
                ("scheduled_date", "<=", fields.Datetime.now()),
            ]
        ):
            activity.run()

    def _activate(self):
        for record in self.filtered(lambda r: not r.scheduled_date):
            config = record.configuration_activity_id
            record.scheduled_date = fields.Datetime.now() + relativedelta(
                **{config.trigger_interval_type: config.trigger_interval}
            )

    def _set_mail_bounced(self):
        self.write({"mail_status": "bounce"})
        self.child_ids.filtered(
            lambda r: r.trigger_type == "mail_bounce"
            and not r.scheduled_date
            and r.state == "scheduled"
        )._activate()
