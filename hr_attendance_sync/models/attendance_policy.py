# -*- coding: utf-8 -*-
from odoo import fields, models

class DahuaAttendancePolicy(models.Model):
    _name = "dahua.attendance.policy"
    _description = "Attendance Policy"
    _rec_name = "employee_name"

    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        required=True,
        ondelete="cascade",
        index=True,
    )
    employee_name = fields.Char(related="employee_id.name", store=True)
    dahua_user_id = fields.Char(
        related="employee_id.dahua_user_id",
        string="Dahua User ID",
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("uniq_employee_id", "unique(employee_id)", "An employee can only have one attendance exclusion."),
    ]
