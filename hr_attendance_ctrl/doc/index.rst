HR Attendance Control
=====================

HR Attendance Control identifies the configured office polygon associated with Odoo 19 systray check-in and check-out.

Requirements
------------

* Odoo 19 Community or Enterprise on Odoo.sh or on-premise.
* PostgreSQL with the PostGIS extension enabled.
* HTTPS and browser geolocation permission.

Configuration
-------------

#. Enable PostGIS in the target database before installation.
#. Install the module.
#. Open Attendances > Office Locations.
#. Create an office and define its polygon using WKT or the map editor.
#. Use standard Odoo systray attendance actions.

Stored information
------------------

The module stores check-in/check-out coordinates and the matching office on ``hr.attendance``. It identifies the office but does not block attendance outside configured polygons.

Privacy
-------

GPS is read only after browser permission is granted. Coordinates and the matching office are stored in Odoo attendance records. No telemetry or usage analytics are collected.
