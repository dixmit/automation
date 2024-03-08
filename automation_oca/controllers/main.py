# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

from odoo import http, tools
from odoo.http import Response, request
from odoo.tools import consteq


class AutomationOCAController(http.Controller):
    # ------------------------------------------------------------
    # TRACKING
    # ------------------------------------------------------------

    @http.route(
        "/automation_oca/track/<int:record_id>/<string:token>/blank.gif",
        type="http",
        auth="public",
    )
    def automation_oca_mail_open(self, record_id, token, **post):
        """Email tracking. Blank item added.
        We will return the blank item allways, but we will make the request only if
        the data is correct"""
        if consteq(
            token,
            tools.hmac(request.env(su=True), "automation_oca-mail-open", record_id),
        ):
            request.env["automation.record.activity"].sudo().browse(
                record_id
            )._set_mail_open()
        response = Response()
        response.mimetype = "image/gif"
        response.data = base64.b64decode(
            b"R0lGODlhAQABAIAAANvf7wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
        )

        return response
