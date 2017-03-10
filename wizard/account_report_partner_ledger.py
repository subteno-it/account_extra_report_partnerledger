# -*- coding: utf-8 -*-
##############################################################################
#
#    account_extra_report_partnerledger module for OpenERP, Review report partnerledger from account_extra_reports
#    Copyright (C) 2016 SYLEAM Info Services (<http://www.syleam.fr>)
#              Sebastien LANGE <sebastien.lange@syleam.fr>
#
#    This file is a part of account_extra_report_partnerledger
#
#    account_extra_report_partnerledger is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    account_extra_report_partnerledger is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from datetime import datetime
from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class AccountPartnerLedger(models.TransientModel):
    _inherit = "account.common.partner.report"
    _name = "account.report.partner.ledger"
    _description = "Account Partner Ledger"

    amount_currency = fields.Boolean("With Currency", help="It adds the currency column on report if the currency differs from the company currency.")
    reconciled = fields.Boolean('With Reconciled Entries')
    rem_futur_reconciled = fields.Boolean('Reconciled Entries matched with futur is considered like unreconciled.', default=True, help="Matching number in futur is replace by *.")
    partner_ids = fields.Many2many(comodel_name='res.partner', string='Partners', domain=['|', ('is_company', '=', True), ('parent_id', '=', False)], help='If empty, get all partners')
    account_exclude_ids = fields.Many2many(comodel_name='account.account', string='Accounts to exclude', domain=[('internal_type', 'in', ('receivable', 'payable'))], help='If empty, get all accounts')
    date_from_init = fields.Date('Start Date')

    @api.multi
    def pre_print_report(self, data):
        data['form'].update({'partner_ids': self.partner_ids.ids,
                             'account_exclude_ids': self.account_exclude_ids.ids,
                             'date_from_init': self.date_from_init,
                             })
        return super(AccountPartnerLedger, self).pre_print_report(data)

    # FIXME : find an other solution to pass context instead of rewrite this code
    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update({'reconciled': self.reconciled,
                             'rem_futur_reconciled': self.rem_futur_reconciled,
                             'amount_currency': self.amount_currency
                             })
        return self.env['report'].with_context(landscape=True).get_action(self, 'account_extra_report_partnerledger.report_partnerledger', data=data)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
