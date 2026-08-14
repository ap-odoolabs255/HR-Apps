from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestAttendanceOfficeLocation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({'name': 'Location Test Employee'})
        cls.office = cls.env['office.location'].create({
            'name': 'Location Test Office',
            'geom_wkt': False,
        })

    def test_checkin_office_is_stored_from_coordinates(self):
        Attendance = self.env['hr.attendance']
        with patch.object(type(Attendance), '_get_office_by_coords', return_value=self.office):
            attendance = Attendance.create({
                'employee_id': self.employee.id,
                'in_latitude': -6.2,
                'in_longitude': 106.8,
            })
        self.assertEqual(attendance.checkin_office_location_id, self.office)

    def test_checkout_office_is_stored_from_coordinates(self):
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
        })
        with patch.object(type(attendance), '_get_office_by_coords', return_value=self.office):
            attendance.write({
                'out_latitude': -6.2,
                'out_longitude': 106.8,
            })
        self.assertEqual(attendance.checkout_office_location_id, self.office)
