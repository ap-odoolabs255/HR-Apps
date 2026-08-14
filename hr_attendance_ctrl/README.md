# HR Attendance Control

Polygon-based office identification for Odoo 19 Attendance.

## Features

- Configure multiple office areas as WKT polygons.
- Draw office polygons using the included map editor.
- Display the detected office and browser GPS coordinates in the attendance menu.
- Store check-in and check-out coordinates on `hr.attendance`.
- Store the matching office in `checkin_office_location_id` and `checkout_office_location_id`.
- Show office locations in attendance form and list views.
- Provide a loading guard during systray check-in and check-out.

The module identifies and records the matching office. It does not block attendance outside configured polygons.

## Requirements

- Odoo 19 Community or Enterprise, deployed on Odoo.sh or on-premise.
- PostgreSQL with the PostGIS extension installed and enabled in the target database.
- HTTPS and browser geolocation permission for reliable GPS access.
- Internet access to OpenStreetMap tile images while using the polygon editor.

This module is not compatible with Odoo Online because it requires a PostgreSQL extension and custom server-side code.

## Installation

1. Install PostGIS on the PostgreSQL server.
2. Enable it in the target database using `CREATE EXTENSION IF NOT EXISTS postgis;`.
3. Add the module to the Odoo addons path and update the Apps list.
4. Install HR Attendance Control.
5. Open Attendances > Office Locations and configure at least one polygon.

## Privacy

When a user opens the attendance menu and grants browser permission, the module reads GPS coordinates. On check-in or check-out, those coordinates and the matching configured office are stored in the attendance record. No usage analytics or telemetry are collected by this module. OpenStreetMap receives normal tile-image requests when an administrator uses the polygon editor.

## Support

support@apodoolabs.com
