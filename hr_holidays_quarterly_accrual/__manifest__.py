{
    'name': 'HR Holidays Quarterly Accrual',
    'version': '19.0.1.0.1',
    'summary': 'Quarterly accrual every three months from each allocation start date',
    'category': 'Generic Modules/Human Resources',
    'author': 'AP Odoo Labs',
    'website': 'https://apodoolabs.com',
    'support': 'support@apodoolabs.com',
    'license': 'LGPL-3',
    'depends': ['hr_holidays'],
    'images': ['static/description/banner.png'],
    'data': [
        'views/hr_leave_accrual_level_views.xml',
    ],
    'installable': True,
    'application': False,
}
