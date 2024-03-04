# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class AutomationTestCase(TransactionCase):
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
        cls.error_action = cls.env["ir.actions.server"].create(
            {
                "name": "Demo action",
                "state": "code",
                "model_id": cls.env.ref("base.model_res_partner").id,
                "code": "raise UserError('ERROR')",
            }
        )
        cls.template = cls.env["mail.template"].create(
            {
                "name": "My template",
                "model_id": cls.env.ref("base.model_res_partner").id,
                "subject": "Subject",
                "body_html": "My templae",
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

    @classmethod
    def create_mail_activity(cls, parent_id=False, **kwargs):
        return cls.env["automation.configuration.activity"].create(
            {
                "name": "Demo activity",
                "parent_id": parent_id,
                "configuration_id": cls.configuration.id,
                "activity_type": "mail",
                "mail_template_id": cls.template.id,
                "trigger_type": "activity" if parent_id else "start",
                **kwargs,
            }
        )
