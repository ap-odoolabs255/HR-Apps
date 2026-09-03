# -*- coding: utf-8 -*-
import logging
import re
from collections import defaultdict
from datetime import datetime, time, timedelta, timezone

import pytz
import requests
from requests.auth import HTTPDigestAuth
from requests.exceptions import RequestException

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    dahua_user_id = fields.Char(
        string="Dahua User ID", copy=False, index=True,
        groups="hr_attendance.group_hr_attendance_manager",
        help="User ID sent by the Dahua attendance device.",
    )

    _sql_constraints = [("dahua_user_id_unique", "unique(dahua_user_id)", "The Dahua User ID must be unique per employee.")]


class DahuaDeviceConfig(models.Model):
    _name = "dahua.device.config"
    _description = "Dahua Device Configuration"
    _order = "name"

    name = fields.Char(string="Device Name", required=True)
    ip = fields.Char(string="Device URL", required=True, help="Full base URL, for example https://192.0.2.10.")
    username = fields.Char(required=True)
    password = fields.Char(required=True, copy=False)
    verify_ssl = fields.Boolean(string="Verify TLS Certificate", default=True, help="Disable only for a trusted device using a self-signed certificate.")
    active = fields.Boolean(default=True)

    def _normalized_url(self):
        self.ensure_one()
        url = (self.ip or "").strip().rstrip("/")
        if not re.match(r"^https?://", url, flags=re.IGNORECASE):
            raise ValidationError("Device URL must start with http:// or https://.")
        return url

    def _session(self):
        self.ensure_one()
        session = requests.Session()
        session.auth = HTTPDigestAuth(self.username, self.password)
        session.verify = self.verify_ssl
        session.headers.update({"Accept": "*/*", "User-Agent": "Odoo Dahua Attendance Sync"})
        return session

    def action_test_device(self):
        self.ensure_one()
        session = self._session()
        try:
            response = session.get(
                "%s/cgi-bin/magicBox.cgi" % self._normalized_url(),
                params={"action": "getDeviceType"}, timeout=(5, 20),
            )
            response.raise_for_status()
        except RequestException as exc:
            raise UserError("Unable to connect to the device: %s" % exc) from exc
        finally:
            session.close()
        return {"type": "ir.actions.client", "tag": "display_notification", "params": {
            "title": "Dahua Device", "message": "Connection successful.", "type": "success", "sticky": False,
        }}


class DahuaScheduleConfig(models.Model):
    _name = "dahua.schedule.config"
    _description = "Dahua Import Schedule Configuration"
    _order = "id desc"

    name = fields.Char(default="Default", required=True)
    mode = fields.Selection([("auto", "Automatic lookback"), ("manual", "Manual date range")], default="auto", required=True)
    days = fields.Integer(string="Lookback Days", default=1)
    start_time = fields.Datetime(string="Start")
    end_time = fields.Datetime(string="End")
    timezone = fields.Selection(selection=lambda self: [(tz, tz) for tz in pytz.all_timezones], default="Asia/Jakarta", required=True)

    @api.constrains("mode", "days", "start_time", "end_time")
    def _check_period(self):
        for record in self:
            if record.mode == "auto" and record.days <= 0:
                raise ValidationError("Lookback Days must be greater than zero.")
            if record.mode == "manual":
                if not record.start_time or not record.end_time:
                    raise ValidationError("Start and End are required for a manual range.")
                if record.start_time >= record.end_time:
                    raise ValidationError("End must be later than Start.")

    @api.model
    def get_active_config(self):
        config = self.search([], limit=1)
        return config or self.create({"name": "Default"})

    def utc_period(self):
        self.ensure_one()
        if self.mode == "manual":
            return fields.Datetime.to_datetime(self.start_time), fields.Datetime.to_datetime(self.end_time)
        end_utc = fields.Datetime.now()
        return end_utc - timedelta(days=self.days), end_utc


class DahuaAttendanceLog(models.Model):
    _name = "dahua.attendance.log"
    _description = "Dahua Attendance Log"
    _order = "event_datetime desc, id desc"

    device_id = fields.Many2one("dahua.device.config", required=True, ondelete="restrict", index=True)
    card_name = fields.Char(index=True)
    user_id = fields.Char(string="Dahua User ID", required=True, index=True)
    event_timestamp = fields.Integer(required=True, index=True)
    event_datetime = fields.Datetime(required=True, index=True)
    synced = fields.Boolean(default=False, index=True, copy=False)

    _sql_constraints = [("device_event_unique", "unique(device_id, user_id, event_timestamp)", "This device event has already been imported.")]


class DahuaAttendanceService(models.AbstractModel):
    _name = "dahua.attendance.service"
    _description = "Dahua Attendance Synchronization Service"

    @api.model
    def _parse_records(self, response):
        records = defaultdict(dict)
        pattern = re.compile(r"^records\[(\d+)\]\.([A-Za-z0-9_]+)=(.*)$")
        for raw_line in response.iter_lines(decode_unicode=True):
            if raw_line:
                match = pattern.match(raw_line.strip())
                if match:
                    index, key, value = match.groups()
                    records[int(index)][key] = value.strip()
        return records.values()

    @api.model
    def cron_import_logs(self):
        schedule = self.env["dahua.schedule.config"].sudo().get_active_config()
        start_utc, end_utc = schedule.utc_period()
        start_timestamp = int(start_utc.replace(tzinfo=timezone.utc).timestamp())
        end_timestamp = int(end_utc.replace(tzinfo=timezone.utc).timestamp())
        devices = self.env["dahua.device.config"].sudo().search([("active", "=", True)])
        if not devices:
            _logger.info("Dahua import skipped: no active devices.")
            return True
        Log = self.env["dahua.attendance.log"].sudo()
        for device in devices:
            session = device._session()
            try:
                response = session.get(
                    "%s/cgi-bin/recordFinder.cgi" % device._normalized_url(),
                    params={"action": "find", "name": "AccessControlCardRec", "StartTime": start_timestamp, "EndTime": end_timestamp, "Count": "1000"},
                    timeout=(5, 60), stream=True,
                )
                response.raise_for_status()
                created = 0
                for item in self._parse_records(response):
                    user_id = item.get("UserID")
                    try:
                        event_timestamp = int(item.get("CreateTime"))
                    except (TypeError, ValueError):
                        continue
                    if not user_id or Log.search_count([("device_id", "=", device.id), ("user_id", "=", user_id), ("event_timestamp", "=", event_timestamp)], limit=1):
                        continue
                    Log.create({
                        "device_id": device.id, "card_name": item.get("CardName"), "user_id": user_id,
                        "event_timestamp": event_timestamp,
                        "event_datetime": datetime.fromtimestamp(event_timestamp, tz=timezone.utc).replace(tzinfo=None),
                    })
                    created += 1
                _logger.info("Imported %s Dahua logs from %s.", created, device.display_name)
            except RequestException:
                _logger.exception("Unable to import Dahua logs from %s.", device.display_name)
            finally:
                session.close()
        return True

    @api.model
    def cron_sync_attendance(self):
        schedule = self.env["dahua.schedule.config"].sudo().get_active_config()
        logs = self.env["dahua.attendance.log"].sudo().search([
            ("synced", "=", False),
        ], order="event_datetime, id")
        if not logs:
            return True
        employees = self.env["hr.employee"].sudo().search([("dahua_user_id", "!=", False)])
        employee_by_user = {employee.dahua_user_id: employee for employee in employees}
        excluded_ids = set(self.env["dahua.attendance.policy"].sudo().search([("active", "=", True)]).mapped("employee_id").ids)
        local_tz = pytz.timezone(schedule.timezone)
        grouped = defaultdict(lambda: self.env["dahua.attendance.log"])
        unmatched = self.env["dahua.attendance.log"]
        for log in logs:
            employee = employee_by_user.get(log.user_id)
            if not employee or employee.id in excluded_ids:
                unmatched |= log
                continue
            utc_aware = pytz.utc.localize(fields.Datetime.to_datetime(log.event_datetime))
            grouped[(employee.id, utc_aware.astimezone(local_tz).date())] |= log

        Attendance = self.env["hr.attendance"].sudo()
        for (employee_id, local_date), day_logs in grouped.items():
            day_start_local = local_tz.localize(datetime.combine(local_date, time.min))
            next_day_local = day_start_local + timedelta(days=1)
            day_start_utc = day_start_local.astimezone(pytz.utc).replace(tzinfo=None)
            next_day_utc = next_day_local.astimezone(pytz.utc).replace(tzinfo=None)
            event_datetimes = [fields.Datetime.to_datetime(log.event_datetime) for log in day_logs]
            first_event, last_event = min(event_datetimes), max(event_datetimes)
            existing = Attendance.search([
                ("employee_id", "=", employee_id), ("check_in", ">=", day_start_utc), ("check_in", "<", next_day_utc),
            ], order="check_in", limit=1)
            if existing:
                # Treat the existing check-in/check-out and every newly imported
                # log as punches from the same local day. This also handles the
                # common case where check-in and check-out arrive in different
                # cron runs.
                punch_times = [existing.check_in]
                if existing.check_out:
                    punch_times.append(existing.check_out)
                punch_times.extend(event_datetimes)
                distinct_punches = sorted(set(punch_times))
                values = {"check_in": distinct_punches[0]}
                if len(distinct_punches) > 1:
                    values["check_out"] = distinct_punches[-1]
                existing.write(values)
            else:
                values = {"employee_id": employee_id, "check_in": first_event}
                if len(day_logs) > 1:
                    values["check_out"] = last_event
                Attendance.create(values)
            day_logs.write({"synced": True})
        if unmatched:
            _logger.warning("%s Dahua logs were not synchronized because the employee mapping is missing or excluded.", len(unmatched))
        return True
