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

import time
from openerp import models, api


class ReportPartnerLedger(models.AbstractModel):
    _inherit = 'report.account_extra_reports.report_partnerledger'

    def _lines(self, data, partner):
        full_account = []
        query_get_data = self.env['account.move.line'].with_context(data['form'].get('used_context', {}))._query_get()
        reconcile_clause = "" if data['form']['reconciled'] else ' AND "account_move_line".reconciled = false '
        params = [partner.id, tuple(data['computed']['move_state']), tuple(data['computed']['account_ids'])] + query_get_data[2]
        query = """
            SELECT "account_move_line".id, "account_move_line".date, j.code, acc.code as a_code, acc.name as a_name, "account_move_line".ref, m.name as move_name, "account_move_line".name, "account_move_line".debit, "account_move_line".credit, "account_move_line".amount_currency,"account_move_line".currency_id, c.symbol AS currency_code, afr.name as "matching_number"
            FROM """ + query_get_data[0] + """
            LEFT JOIN account_journal j ON ("account_move_line".journal_id = j.id)
            LEFT JOIN account_account acc ON ("account_move_line".account_id = acc.id)
            LEFT JOIN res_currency c ON ("account_move_line".currency_id=c.id)
            LEFT JOIN account_move m ON (m.id="account_move_line".move_id)
            LEFT JOIN account_full_reconcile afr ON (afr.id="account_move_line".full_reconcile_id)
            WHERE "account_move_line".partner_id = %s
                AND m.state IN %s
                AND "account_move_line".account_id IN %s AND """ + query_get_data[1] + reconcile_clause + """
                ORDER BY "account_move_line".date"""
        self.env.cr.execute(query, tuple(params))
        res = self.env.cr.dictfetchall()
        sum = 0.0
        for r in res:
            r['displayed_name'] = '-'.join(
                r[field_name] for field_name in ('move_name', 'ref', 'name')
                if r[field_name] not in (None, '', '/')
            )
            sum += r['debit'] - r['credit']
            r['progress'] = sum
            full_account.append(r)
        return full_account

    @api.multi
    def render_html(self, data):
        if data['form'].get('partner_ids'):
            data['computed'] = {}

            obj_partner = self.env['res.partner']
            query_get_data = self.env['account.move.line'].with_context(data['form'].get('used_context', {}))._query_get()
            data['computed']['move_state'] = ['draft', 'posted']
            if data['form'].get('target_move', 'all') == 'posted':
                data['computed']['move_state'] = ['posted']
            result_selection = data['form'].get('result_selection', 'customer')
            if result_selection == 'supplier':
                data['computed']['ACCOUNT_TYPE'] = ['payable']
            elif result_selection == 'customer':
                data['computed']['ACCOUNT_TYPE'] = ['receivable']
            else:
                data['computed']['ACCOUNT_TYPE'] = ['payable', 'receivable']

            self.env.cr.execute("""
                SELECT a.id
                FROM account_account a
                WHERE a.internal_type IN %s
                AND NOT a.deprecated""", (tuple(data['computed']['ACCOUNT_TYPE']),))
            data['computed']['account_ids'] = [a for (a,) in self.env.cr.fetchall()]
            params = [tuple(data['computed']['move_state']), tuple(data['computed']['account_ids'])] + query_get_data[2]
            reconcile_clause = "" if data['form']['reconciled'] else ' AND "account_move_line".reconciled = false '
            query = """
                SELECT DISTINCT "account_move_line".partner_id
                FROM """ + query_get_data[0] + """, account_account AS account, account_move AS am
                WHERE "account_move_line".partner_id IS NOT NULL
                    AND "account_move_line".account_id = account.id
                    AND am.id = "account_move_line".move_id
                    AND am.state IN %s
                    AND "account_move_line".account_id IN %s
                    AND NOT account.deprecated
                    AND """ + query_get_data[1] + reconcile_clause
            self.env.cr.execute(query, tuple(params))
            partner_ids = list(set([res['partner_id'] for res in self.env.cr.dictfetchall()]) & set(data['form']['partner_ids']))
            partners = obj_partner.browse(partner_ids)
            partners = sorted(partners, key=lambda x: (x.ref, x.name))

            docargs = {
                'doc_ids': partner_ids,
                'doc_model': self.env['res.partner'],
                'data': data,
                'docs': partners,
                'time': time,
                'lines': self._lines,
                'sum_partner': self._sum_partner,
            }
            return self.env['report'].render('account_extra_reports.report_partnerledger', docargs)
        return super(ReportPartnerLedger, self).render_html(data)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
