# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging
from math import radians, cos, sin, asin, sqrt

_logger = logging.getLogger(__name__)

def haversine(lat1, lon1, lat2, lon2):
    """Hitung jarak (dalam meter) antara dua koordinat menggunakan rumus Haversine"""
    R = 6371000  # Earth radius in meters
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return R * c

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    checkin_office_location_id = fields.Many2one(
        'office.location', string='Office Location (Check-in)', readonly=True)
    checkout_office_location_id = fields.Many2one(
        'office.location', string='Office Location (Check-out)', readonly=True)

    # ------------------------------------------------------------
    # Helper: find office.location by coordinates (polygon coverage)
    # ------------------------------------------------------------
    def _get_office_by_coords(self, latitude, longitude):
        """Return office.location record that covers the given point (lon/lat).

        Uses PostGIS polygon column office_location.the_geom2 (SRID 3857) if available.
        Returns False when:
          - coordinates empty/invalid
          - PostGIS/geometry column not available
          - point is outside all office polygons
        """
        # Validate coordinates
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except Exception:
            return False
        if latitude == 0.0 and longitude == 0.0:
            return False

        cr = self.env.cr

        # Check PostGIS exists
        try:
            cr.execute("SELECT 1 FROM pg_extension WHERE extname = 'postgis'")
            if not cr.fetchone():
                return False
        except Exception:
            return False

        # Check geom column exists
        try:
            cr.execute("""
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'office_location' AND column_name = 'the_geom2'
            """)
            if not cr.fetchone():
                return False
        except Exception:
            return False

        office_id = None
        try:
            cr.execute(
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
            row = cr.fetchone()
            if row:
                office_id = row[0]
        except Exception as e:
            _logger.warning("[hr_attendance_ctrl] office lookup failed: %s", e)
            office_id = None

        return self.env['office.location'].browse(office_id) if office_id else False


    @api.model
    def create(self, vals):
        """Create attendance and auto-fill office location + office name.

        Selain menyimpan ID office ke field:
          - checkin_office_location_id
          - checkout_office_location_id

        Modul ini juga akan mengisi nama office (berdasarkan office.location.name) ke:
          - in_country_name  (untuk check-in)
          - out_country_name (untuk check-out)

        Catatan: field in_country_name / out_country_name diasumsikan sudah ada di model hr.attendance.
        """
        vals = dict(vals or {})
        # Pre-compute check-in office + name
        if vals.get('in_latitude') is not None and vals.get('in_longitude') is not None:
            office = self._get_office_by_coords(vals.get('in_latitude'), vals.get('in_longitude'))
            vals['checkin_office_location_id'] = office.id if office else False
            if 'in_country_name' in self._fields:
                vals['in_country_name'] = office.name if office else False

        # Pre-compute check-out office + name (jika ada saat create)
        if vals.get('out_latitude') is not None and vals.get('out_longitude') is not None:
            office = self._get_office_by_coords(vals.get('out_latitude'), vals.get('out_longitude'))
            vals['checkout_office_location_id'] = office.id if office else False
            if 'out_country_name' in self._fields:
                vals['out_country_name'] = office.name if office else False

        return super(HrAttendance, self).create(vals)

    def write(self, vals):
        # Prevent recursive re-computation when we write derived fields ourselves
        if self.env.context.get('skip_office_location_compute'):
            return super(HrAttendance, self).write(vals)

        res = super(HrAttendance, self).write(vals)

        # Update derived fields (office id + office name) based on coordinates
        for rec in self:
            updates = {}

            # Update check-in office + name
            if 'in_latitude' in vals or 'in_longitude' in vals:
                lat = vals.get('in_latitude', rec.in_latitude)
                lon = vals.get('in_longitude', rec.in_longitude)
                office = rec._get_office_by_coords(lat, lon)
                updates['checkin_office_location_id'] = office.id if office else False
                if 'in_country_name' in rec._fields:
                    updates['in_country_name'] = office.name if office else False

            # Update check-out office + name
            if 'out_latitude' in vals or 'out_longitude' in vals:
                lat = vals.get('out_latitude', rec.out_latitude)
                lon = vals.get('out_longitude', rec.out_longitude)
                office = rec._get_office_by_coords(lat, lon)
                updates['checkout_office_location_id'] = office.id if office else False
                if 'out_country_name' in rec._fields:
                    updates['out_country_name'] = office.name if office else False

            if updates:
                super(HrAttendance, rec.with_context(skip_office_location_compute=True)).write(updates)

        return res
    
    def _get_office_by_coords(self, lat, lon):
        # Cari office.location via polygon the_geom2 (SRID 3857) dengan toleransi boundary
        if lat is None or lon is None:
            return False
        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except Exception:
            return False

        cr = self.env.cr
        try:
            cr.execute(
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
            (lon_f, lat_f, lon_f, lat_f),
            )
            row = cr.fetchone()
            if row and row[0]:
                return self.env['office.location'].browse(row[0])
        except Exception as e:
                _logger.warning("Polygon lookup failed: %s", e)
        return False
