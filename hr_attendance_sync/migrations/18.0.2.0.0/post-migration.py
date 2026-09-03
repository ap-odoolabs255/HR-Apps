# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Clean legacy dynamic jobs and preserve the former employee mapping."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    legacy_names = [
        "Attendance: Get attendance from devices",
        "Attendance: Sync db queue to db attendance",
        "Message One (code)",
        "Message Two (code)",
    ]
    env["ir.cron"].search([("name", "in", legacy_names)]).unlink()
    env["ir.actions.server"].search([("name", "in", legacy_names)]).unlink()

    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_schema = current_schema()
           AND table_name = 'hr_employee'
           AND column_name = 'x_attendance_id'
        """
    )
    if cr.fetchone():
        cr.execute(
            """
            UPDATE hr_employee
               SET dahua_user_id = x_attendance_id::text
             WHERE dahua_user_id IS NULL
               AND x_attendance_id IS NOT NULL
            """
        )
