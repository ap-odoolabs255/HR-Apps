Attendance: One Check-in/Out per Day
====================================

A lightweight Odoo 18 add-on that optionally limits every employee to one
attendance record per local calendar day.

Features
--------

* Enable or disable the rule from **Settings > Attendances > Modes**.
* Calculates the attendance day using the employee/user timezone.
* Shows a clear validation error when a second record is attempted.
* Uses a PostgreSQL partial unique index to protect against concurrent duplicates.
* Returns to standard Odoo behavior when the option is disabled.

Installation
------------

#. Copy ``hr_attendance_daily_limit`` into your Odoo addons path.
#. Update the Apps list.
#. Install **Attendance: One Check-in/Out per Day**.
#. Open **Settings > Attendances > Modes** and enable
   **Attendance Protection (1 per day)**.

Important behavior when enabling
--------------------------------

When the option is enabled for the first time, the module populates the local
attendance date for existing records. If an employee already has multiple
records on the same local date, the module consolidates them: the earliest
record is retained, the latest available check-out is copied to it, and the
additional records are removed.

Back up the database before enabling this rule on a production database that
may already contain duplicate daily attendance records.

Compatibility
-------------

* Odoo 18.0 Community and Enterprise
* Requires the standard ``hr_attendance`` module

License
-------

LGPL-3

Author
------

AP Odoo Labs — https://apodoolabs.com
