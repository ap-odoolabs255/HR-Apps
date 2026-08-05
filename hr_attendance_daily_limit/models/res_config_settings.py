# -*- coding: utf-8 -*-
from odoo import fields, models
import pytz

PARAM_ENABLED = "hr_attendance_daily_limit.enabled"
UNIQUE_INDEX_NAME = "hr_attendance_unique_emp_date_idx"

def _compute_local_date(dt_utc, tz_name, fields_mod):
    if not dt_utc:
        return False
    if isinstance(dt_utc, str):
        dt_utc = fields_mod.Datetime.from_string(dt_utc)
    if dt_utc.tzinfo is None:
        dt_utc = pytz.UTC.localize(dt_utc)
    try:
        tz = pytz.timezone(tz_name or "UTC")
    except Exception:
        tz = pytz.UTC
    return dt_utc.astimezone(tz).date()

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    hr_attendance_daily_limit_enabled = fields.Boolean(
        string="Attendance Protection (1 per day)",
        config_parameter=PARAM_ENABLED,
        help="If enabled, employees cannot create more than one attendance record per day.",
    )

    def _update_attendance_date_all(self):
        Attendance = self.env['hr.attendance'].with_context(active_test=False)
        Employee = self.env['hr.employee'].with_context(active_test=False)

        user_tz = self.env.user.tz or "UTC"
        tz_map = {emp.id: (emp.user_id.tz or user_tz or "UTC") for emp in Employee.search([])}

        cr = self.env.cr
        offset = 0
        limit = 2000
        while True:
            batch = Attendance.search([], offset=offset, limit=limit, order="id")
            if not batch:
                break

            to_write = []
            for rec in batch:
                if not rec.check_in or not rec.employee_id:
                    continue
                tz_name = tz_map.get(rec.employee_id.id) or user_tz or "UTC"
                local_date = _compute_local_date(rec.check_in, tz_name, fields)
                if local_date and rec.attendance_date != local_date:
                    to_write.append((rec.id, local_date))

            if to_write:
                cr.execute("CREATE TEMP TABLE IF NOT EXISTS tmp_att_date (id int, d date) ON COMMIT DROP")
                cr.execute("TRUNCATE tmp_att_date")
                args = ",".join(["(%s,%s)"] * len(to_write))
                flat = []
                for rid, d in to_write:
                    flat.extend([rid, d])
                cr.execute("INSERT INTO tmp_att_date (id, d) VALUES " + args, flat)
                cr.execute("UPDATE hr_attendance h SET attendance_date = t.d FROM tmp_att_date t WHERE h.id = t.id")

            offset += limit

    def set_values(self):
        super().set_values()
        enabled = self.env["ir.config_parameter"].sudo().get_param(PARAM_ENABLED, "0") in ("1", "true", "True")
        cr = self.env.cr

        if enabled:
            self._update_attendance_date_all()

            cr.execute("""
                WITH ranked AS (
                    SELECT id,
                           employee_id,
                           attendance_date,
                           check_in,
                           check_out,
                           ROW_NUMBER() OVER (PARTITION BY employee_id, attendance_date ORDER BY check_in NULLS LAST, id) AS rn
                    FROM hr_attendance
                    WHERE attendance_date IS NOT NULL
                ),
                dups AS (SELECT * FROM ranked WHERE rn > 1),
                prim AS (SELECT * FROM ranked WHERE rn = 1),
                agg AS (
                    SELECT p.id AS primary_id,
                           MAX(d.check_out) AS max_checkout
                    FROM prim p
                    LEFT JOIN dups d
                      ON d.employee_id = p.employee_id AND d.attendance_date = p.attendance_date
                    GROUP BY p.id
                )
                UPDATE hr_attendance h
                   SET check_out = COALESCE(a.max_checkout, h.check_out)
                  FROM agg a
                 WHERE h.id = a.primary_id
                   AND (a.max_checkout IS NOT NULL AND (h.check_out IS NULL OR a.max_checkout > h.check_out));
            """)
            cr.execute("""
                DELETE FROM hr_attendance h
                USING (
                    SELECT id
                    FROM (
                        SELECT id,
                               ROW_NUMBER() OVER (PARTITION BY employee_id, attendance_date ORDER BY check_in NULLS LAST, id) AS rn
                        FROM hr_attendance
                        WHERE attendance_date IS NOT NULL
                    ) t
                    WHERE t.rn > 1
                ) d
                WHERE h.id = d.id;
            """)

            cr.execute(f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_class c
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE c.relname = '{UNIQUE_INDEX_NAME}' AND n.nspname = 'public'
                    ) THEN
                        CREATE UNIQUE INDEX {UNIQUE_INDEX_NAME}
                            ON hr_attendance (employee_id, attendance_date)
                            WHERE attendance_date IS NOT NULL;
                    END IF;
                END$$;
            """)
        else:
            cr.execute(f"DROP INDEX IF EXISTS {UNIQUE_INDEX_NAME};")