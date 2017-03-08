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
    rem_futur_reconciled = fields.Boolean('Without futur matching number', default=True)
    partner_ids = fields.Many2many(comodel_name='res.partner', string='Partners', domain=['|', ('is_company', '=', True), ('parent_id', '=', False)], help='If empty, get all partners')
    account_exclude_ids = fields.Many2many(comodel_name='account.account', string='Accounts to exclude', domain=[('internal_type', 'in', ('receivable', 'payable'))], help='If empty, get all accounts')

    @api.multi
    def pre_print_report(self, data):
        data['form'].update({'partner_ids': self.partner_ids.mapped('id'),
                             'account_exclude_ids': self.account_exclude_ids.mapped('id'),
                             })
        return super(AccountPartnerLedger, self).pre_print_report(data)

    # FIXME : find an other solution to pass context instead of rewrite this code
    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update({'reconciled': self.reconciled,
                             'rem_futur_reconciled': self.rem_futur_reconciled,
                             'amount_currency': self.amount_currency
                             })
        data['reconcile_clause'], data['matching_in_futur'] = self._compute_reconcile_clause(data)

        return self.env['report'].with_context(landscape=True).get_action(self, 'account_extra_report_partnerledger.report_partnerledger', data=data)

    def _compute_reconcile_clause(self, data):
        reconcile_clause = ""
        list_match_in_futur = []
        if not data['form']['reconciled']:
            reconcile_clause = ' AND "account_move_line".reconciled = false '

        if not data['form']['reconciled'] and data['form']['rem_futur_reconciled'] and data['form']['date_to']:
            date_to = datetime.strptime(data['form']['date_to'], DEFAULT_SERVER_DATE_FORMAT)
            acc_ful_obj = self.env['account.full.reconcile']

            for full_rec in acc_ful_obj.search([]):
                in_futur = False
                for date in full_rec.reconciled_line_ids.mapped('date_maturity'):
                    date_move = datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT)
                    if date_move > date_to:
                        in_futur = True
                        break
                if in_futur:
                    list_match_in_futur.append(full_rec.id)

            if list_match_in_futur:
                reconcile_clause = """ AND ("account_move_line".reconciled = false OR "account_move_line".full_reconcile_id IN """ + str(tuple(list_match_in_futur)) + """)"""
        return reconcile_clause, list_match_in_futur


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
