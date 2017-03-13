# -*- coding: utf-8 -*-

{
    'name': 'Extra Accounting Report Partner Ledger',
    'version': '1.0',
    'category': 'Accounting & Finance',
    'author': 'SYLEAM, Florent de Labarre',
    'description': """Extra Accounting Report Partner Ledger""",
    'summary': 'Extra Accounting Report Partner Ledger',
    'website': 'www.syleam.com',
    'depends': ['account'],
    'data': [
        'data/account_report.xml',
        'views/report_partnerledger.xml',
        'wizard/account_report_partner_ledger_view.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}
