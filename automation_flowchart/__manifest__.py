# Copyright 2025 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Automation Flowchart",
    "summary": """Posibility of adding a flowchart to represent the automation actions.""",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "Dixmit,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/automation",
    "depends": [
        "automation_oca",
    ],
    "data": [
        "views/automation_flowchart.xml",
        "security/ir.model.access.csv",
    ],
    "demo": [],
    "assets": {
        "web.assets_backend": [
            "automation_flowchart/static/src/flowchart/flowchart_action.esm.js",
            "automation_flowchart/static/src/flowchart/flowchart.xml",
        ],
    },
}
