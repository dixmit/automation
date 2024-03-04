# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Automation Oca",
    "summary": """
        Automate actions in threaded models""",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "category": "Automation",
    "author": "Dixmit,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/automation",
    "depends": ["mail"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/menu.xml",
        "views/automation_record.xml",
        "views/automation_record_activity.xml",
        "views/automation_configuration_activity.xml",
        "views/automation_configuration.xml",
        "data/cron.xml",
    ],
    "demo": [],
}
