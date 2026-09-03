{
    "name": "Dahua HR Attendance Sync",
    "version": "18.0.2.1.0",
    "summary": "Import Dahua access logs and synchronize employee attendances",
    "description": """
Dahua HR Attendance Sync
========================

Collect access-control logs from one or more Dahua devices, retain an audit
history in Odoo, and create or update daily employee attendance records.
    """,
    "category": "Human Resources/Attendances",
    "website": "https://apodoolabs.com/",
    "support": "support@apodoolabs.com",
    "author": "AP Odoo Labs",
    "maintainer": "AP Odoo Labs",
    "license": "LGPL-3",
    "depends": ["hr_attendance"],
    "external_dependencies": {"python": ["requests", "pytz"]},
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/config_views.xml",
    ],
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
