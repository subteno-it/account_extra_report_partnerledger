# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Extra Accounting Report Partner Ledger',
    'version': '1.0',
    'category': 'Accounting & Finance',
    'description': """
Extra Accounting Report Partner Ledger.
====================================

This module modify report:
* Partner Ledger
    """,
    'website': 'https://www.odoo.com/page/accounting',
    'depends': [
        'account_extra_reports',
        'account_full_reconcile',
    ],
    'data': [
        'views/report_partnerledger.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}
