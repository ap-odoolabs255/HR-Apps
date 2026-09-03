# Dahua HR Attendance Sync

Free Odoo 18 add-on for importing access logs from Dahua devices and synchronizing them with Odoo Attendances.

## Features

- Multiple Dahua devices with HTTP Digest authentication.
- Native Odoo staging log with duplicate protection and audit trail.
- Employee mapping through **Dahua User ID**.
- Daily first-punch/last-punch attendance synchronization in a configurable timezone.
- Reliable check-out updates when punches arrive in separate synchronization runs.
- Optional employee exclusion list.
- Two disabled-by-default scheduled actions for safe setup.

## Setup

1. Install the module and open **Settings > Technical > Dahua Attendance**.
2. Add each device and test its connection.
3. Set a unique Dahua User ID on each employee.
4. Review Import Settings and its timezone.
5. Enable **Dahua Attendance: Import device logs** and **Dahua Attendance: Synchronize attendances** under Scheduled Actions.

The Odoo server must be able to reach each device. Keep TLS certificate verification enabled whenever the device has a valid certificate.

The synchronization job retries every unsynchronized staging log regardless of the import lookback period. Logs without an employee mapping remain pending until the mapping is added.

## Compatibility

- Odoo 18.0 Community and Enterprise
- Python packages: `requests`, `pytz` (normally included with Odoo)

## License

LGPL-3. See `LICENSE`.
