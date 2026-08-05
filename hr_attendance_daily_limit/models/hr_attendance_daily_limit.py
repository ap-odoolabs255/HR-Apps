# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import pytz

try:
    from psycopg2 import IntegrityError
except Exception:
    IntegrityError = Exception

PARAM_ENABLED = "hr_attendance_daily_limit.enabled"
UNIQUE_INDEX_NAME = "hr_attendance_unique_emp_date_idx"

class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    attendance_date = fields.Date(
        string="Attendance Date (Local)",
        compute="_compute_attendance_date",
        store=True,
        index=True,
        help="Local calendar date (based on employee/user timezone) derived from check-in. "
             "Used to enforce the 'one attendance per day' rule when enabled in Settings.",
    )

    @api.depends("check_in")
    def _compute_attendance_date(self):
        for rec in self:
            rec.attendance_date = rec._attendance_local_date_from_dt()

    def _attendance_local_date_from_dt(self, dt_utc=None, employee=None):
        self.ensure_one()
        dt_utc = dt_utc or self.check_in
        employee = employee or self.employee_id
        if not dt_utc or not employee:
            return False

        tz_name = (employee.user_id.tz or
                   self.env.context.get("tz") or
                   self.env.user.tz or
                   "UTC")
        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            tz = pytz.UTC

        dt = fields.Datetime.from_string(dt_utc) if isinstance(dt_utc, str) else dt_utc
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        return dt.astimezone(tz).date()

    def _raise_daily_limit(self, employee, att_date):
        raise ValidationError(_(
            "Attendance protection is enabled: only one attendance (check-in/check-out) is allowed per day "
            "for employee %(emp)s (date: %(date)s)."
        ) % {
            "emp": employee.name or employee.id,
            "date": att_date,
        })

    @api.model_create_multi
    def create(self, vals_list):
        enabled = self.env["ir.config_parameter"].sudo().get_param(PARAM_ENABLED, "0") in ("1", "true", "True")
        if not enabled:
            return super().create(vals_list)

        employees = self.env["hr.employee"].browse([v.get("employee_id") for v in vals_list if v.get("employee_id")])
        emp_map = {e.id: e for e in employees}

        new_vals_list = []
        for vals in vals_list:
            vals = dict(vals)
            emp = emp_map.get(vals.get("employee_id"))
            check_in = vals.get("check_in")
            if emp and check_in:
                dummy = self.new({"employee_id": emp.id, "check_in": check_in})
                att_date = dummy._attendance_local_date_from_dt(dt_utc=check_in, employee=emp)
                if att_date:
                    vals["attendance_date"] = att_date
                    exists = self.search_count([
                        ("employee_id", "=", emp.id),
                        ("attendance_date", "=", att_date),
                    ])
                    if exists:
                        self._raise_daily_limit(emp, att_date)
            new_vals_list.append(vals)

        try:
            return super().create(new_vals_list)
        except IntegrityError as e:
            msg = str(getattr(e, "diag", "") or e)
            if UNIQUE_INDEX_NAME in msg or ("attendance_date" in msg and "employee_id" in msg):
                last = new_vals_list[-1] if new_vals_list else {}
                emp = emp_map.get(last.get("employee_id")) or self.env["hr.employee"].browse(last.get("employee_id"))
                att_date = last.get("attendance_date")
                if emp and att_date:
                    self._raise_daily_limit(emp, att_date)
                raise ValidationError(_(
                    "Attendance protection is enabled: only one attendance per day is allowed."
                ))
            raise

    def write(self, vals):
        enabled = self.env["ir.config_parameter"].sudo().get_param(PARAM_ENABLED, "0") in ("1", "true", "True")
        if enabled and "check_in" in vals:
            for rec in self:
                emp = rec.employee_id
                check_in = vals.get("check_in")
                if emp and check_in:
                    att_date = rec._attendance_local_date_from_dt(dt_utc=check_in, employee=emp)
                    if att_date:
                        exists = self.search_count([
                            ("id", "!=", rec.id),
                            ("employee_id", "=", emp.id),
                            ("attendance_date", "=", att_date),
                        ])
                        if exists:
                            rec._raise_daily_limit(emp, att_date)
                        vals = dict(vals, attendance_date=att_date)
                        try:
                            return super(HrAttendance, rec).write(vals)
                        except IntegrityError as e:
                            msg = str(getattr(e, "diag", "") or e)
                            if UNIQUE_INDEX_NAME in msg:
                                rec._raise_daily_limit(emp, att_date)
                            raise
        try:
            return super().write(vals)
        except IntegrityError as e:
            msg = str(getattr(e, "diag", "") or e)
            if enabled and UNIQUE_INDEX_NAME in msg:
                rec = self[:1]
                if rec and rec.employee_id and rec.attendance_date:
                    rec._raise_daily_limit(rec.employee_id, rec.attendance_date)
                raise ValidationError(_(
                    "Attendance protection is enabled: only one attendance per day is allowed."
                ))
            raise