{
    'name': 'HR Holidays Quarterly Accrual',
    'version': '18.0.1.2.0',
    'summary': 'Quarterly accrual every three months from each allocation start date',
    'category': 'Human Resources/Time Off',
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