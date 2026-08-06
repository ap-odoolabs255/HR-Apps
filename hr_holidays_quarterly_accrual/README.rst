HR Holidays Quarterly Accrual
===============================

Adds a ``Quarterly`` frequency to Odoo 19 Time Off accrual plans.

The three-month cycle is anchored to each employee allocation's Start Date.
For example, an allocation starting on 15 April accrues on 15 July,
15 October, 15 January, and so on.

Recommended configuration
-------------------------

* Employee accrue: for example, 4 Days
* Frequency: Quarterly
* Start Accruing: 0 Months after allocation start date
* Accrued Gain Time: At the end of the accrual period

Installation
------------

1. Copy the module into an Odoo addons directory.
2. Restart Odoo and update the Apps list.
3. Install ``HR Holidays Quarterly Accrual``.
4. Configure a Quarterly milestone in Time Off accrual plans.

Author
------

AP Odoo Labs — https://apodoolabs.com
