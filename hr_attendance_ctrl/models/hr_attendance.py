# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models


_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    checkin_office_location_id = fields.Many2one(
        "office.location",
        string="Office Location (Check-in)",
        readonly=True,
        ondelete="set null",
    )
    checkout_office_location_id = fields.Many2one(
        "office.location",
        string="Office Location (Check-out)",
        readonly=True,
        ondelete="set null",
    )

    def _get_office_by_coords(self, latitude, longitude):
        """Return the first office polygon covering the WGS84 coordinate."""
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError):
            return self.env["office.location"]

        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            return self.env["office.location"]

        self.env.cr.execute(
            """
            SELECT id
              FROM office_location
             WHERE the_geom2 IS NOT NULL
               AND ST_IsValid(the_geom2)
               AND (
                    ST_Covers(
                        the_geom2,
                        ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), 4326), 3857)
                    )
                    OR ST_DWithin(
                        the_geom2,
                        ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), 4326), 3857),
                        5
                    )
               )
             ORDER BY id
             LIMIT 1
            """,
            (longitude, latitude, longitude, latitude),
        )
        row = self.env.cr.fetchone()
        return self.env["office.location"].browse(row[0]) if row else self.env["office.location"]

    def _add_office_locations(self, vals):
        vals = dict(vals)
        if "in_latitude" in vals or "in_longitude" in vals:
            office = self._get_office_by_coords(
                vals.get("in_latitude"), vals.get("in_longitude")
            )
            vals["checkin_office_location_id"] = office.id or False
        if "out_latitude" in vals or "out_longitude" in vals:
            office = self._get_office_by_coords(
                vals.get("out_latitude"), vals.get("out_longitude")
            )
            vals["checkout_office_location_id"] = office.id or False
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        # Odoo 19's hr.attendance create API is multi-record.
        return super().create([self._add_office_locations(vals) for vals in vals_list])

    def write(self, vals):
        result = super().write(vals)
        coordinate_fields = {
            "in_latitude",
            "in_longitude",
            "out_latitude",
            "out_longitude",
        }
        if not coordinate_fields.intersection(vals):
            return result

        for attendance in self:
            updates = {}
            if {"in_latitude", "in_longitude"}.intersection(vals):
                office = attendance._get_office_by_coords(
                    attendance.in_latitude, attendance.in_longitude
                )
                updates["checkin_office_location_id"] = office.id or False
            if {"out_latitude", "out_longitude"}.intersection(vals):
                office = attendance._get_office_by_coords(
                    attendance.out_latitude, attendance.out_longitude
                )
                updates["checkout_office_location_id"] = office.id or False
            if updates:
                super(HrAttendance, attendance).write(updates)
        return result
