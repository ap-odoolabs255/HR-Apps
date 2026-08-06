# -*- coding: utf-8 -*-
{
    "name": "Attendance: One Check-in/Out per Day",
    "summary": "Optional protection that limits each employee to one attendance record per local calendar day.",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "author": "AP Odoo Labs",
    "maintainer": "AP Odoo Labs",
    "website": "https://apodoolabs.com",
    "support": "support@apodoolabs.com",
    "category": "Human Resources/Attendances",
    "depends": ["hr_attendance"],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "images": [
        "static/description/banner.png",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
