# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import time
from odoo import api, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class ReportPartnerLedger(models.AbstractModel):
    _name = 'report.account_extra_report_partnerledger.report_partnerledger'

    def _generate_sql(self, data, accounts, date_to=False):
        date_clause = ''
        if date_to:
            date_clause += ' AND "account_move_line"."date" <= ' + "'" + str(date_to) + "'" + ' '

        # on efface les dates sinon cela est pris en compte dans la requête SQL
        data['form']['used_context']['date_to'] = False
        data['form']['used_context']['date_from'] = False

        query_get_data = self.env['account.move.line'].with_context(data['form'].get('used_context', {}))._query_get()
        reconcile_clause = data['reconcile_clause']
        params = [tuple(data['computed']['move_state']), tuple(accounts.ids)] + query_get_data[2]

        if data['form'].get('partner_ids'):
            partner_ids = data['form'].get('partner_ids')
            if len(partner_ids) == 1:
                partner_ids = "(%s)" % (partner_ids[0])
            else:
                partner_ids = tuple(partner_ids)
            partner_clause = ' AND "account_move_line".partner_id IN ' + str(partner_ids) + ' '
        else:
            partner_clause = ' AND "account_move_line".partner_id IS NOT NULL '

        query = """
            SELECT "account_move_line".id, "account_move_line".date, "account_move_line".date_maturity, j.code, acc.code as a_code, acc.name as a_name, "account_move_line".ref, m.name as move_name, "account_move_line".name, "account_move_line".debit, "account_move_line".credit, "account_move_line".amount_currency,"account_move_line".currency_id, c.symbol AS currency_code, afr.name as "matching_number", afr_id.id as "matching_number_id", "account_move_line".partner_id, "account_move_line".account_id
            FROM """ + query_get_data[0] + """
            LEFT JOIN account_journal j ON ("account_move_line".journal_id = j.id)
            LEFT JOIN account_account acc ON ("account_move_line".account_id = acc.id)
            LEFT JOIN res_currency c ON ("account_move_line".currency_id=c.id)
            LEFT JOIN account_move m ON (m.id="account_move_line".move_id)
            LEFT JOIN account_full_reconcile afr ON (afr.id="account_move_line".full_reconcile_id)
            LEFT JOIN account_full_reconcile afr_id ON (afr_id.id="account_move_line".full_reconcile_id)
            WHERE
                m.state IN %s
                AND "account_move_line".account_id IN %s AND """ + query_get_data[1] + reconcile_clause + partner_clause + date_clause + """
                ORDER BY "account_move_line".date"""
        self.env.cr.execute(query, tuple(params))
        return self.env.cr.dictfetchall()

    def _generate_account_dict(self, accounts):
        line_account = {}
        for account in accounts:
            line_account[account.id] = {
                'debit': 0.0,
                'credit': 0.0,
                'balance': 0.0,
                'code': account.code,
                'name': account.name,
                'active': False,
            }
        return line_account

    def _generate_init_balance_lines(self, init_account):
        init = []
        for key, value in init_account.items():
            init_debit = value['init_debit']
            init_credit = value['init_credit']
            with_init = True
            if round(init_debit - init_credit, 4) > 0:
                init_debit = init_debit - init_credit
                init_credit = 0
            elif round(init_debit - init_credit, 4) < 0:
                init_credit = init_credit - init_debit
                init_debit = 0
            else:
                with_init = False
            if with_init:
                init.append({'date': 'Initial balance',
                             'date_maturity': '',
                             'debit': init_debit,
                             'credit': init_credit,
                             'code': '',
                             'a_code': value['a_code'],
                             'account_id': key,
                             'displayed_name': '',
                             'progress': 0.0,
                             'amount_currency': 0.0,
                             'matching_number': '',
                             'report': True})
        return init

    def _generate_data(self, data, accounts):
        lang_code = self.env.context.get('lang') or 'en_US'
        lang = self.env['res.lang']
        lang_id = lang._lang_get(lang_code)
        date_format = lang_id.date_format

        with_init_balance = data['form']['with_init_balance']
        date_from = data['form']['used_context']['date_from']
        date_to = data['form']['used_context']['date_to']
        date_from_dt = datetime.strptime(date_from, DEFAULT_SERVER_DATE_FORMAT) if date_from else False
        date_to_dt = datetime.strptime(date_to, DEFAULT_SERVER_DATE_FORMAT) if date_to else False

        res = self._generate_sql(data, accounts, date_to=date_to)

        line_partner = {}
        partner_ids = []
        # renagement par partner
        for line in res:
            if line['partner_id'] in line_partner.keys():
                line_partner[line['partner_id']]['lines'].append(line)
            else:
                line_partner.update({line['partner_id']: {'lines': [line],
                                                          'new_lines': [], }})

        line_account = self._generate_account_dict(accounts)

        for partner, value in line_partner.items():
            init_account = {}
            new_list = []
            for r in value['lines']:
                date_move_dt = datetime.strptime(r['date'], DEFAULT_SERVER_DATE_FORMAT)

                move_matching = True if r['matching_number_id'] else False
                move_matching_in_futur = False
                if r['matching_number_id'] in data['matching_in_futur']:
                    move_matching = False
                    move_matching_in_futur = True

                # on ne met dans la balance initiale que les mouvements non lettrées
                # et a une date inféreieure à date_from
                if with_init_balance and date_from_dt and date_move_dt < date_from_dt and move_matching:
                    if r['account_id'] in init_account.keys():
                        init_account[r['account_id']]['init_debit'] += r['debit']
                        init_account[r['account_id']]['init_credit'] += r['credit']
                    else:
                        init_account[r['account_id']] = {'init_debit': r['debit'],
                                                         'init_credit': r['credit'],
                                                         'a_code': r['a_code'], }

                else:
                    date_move = datetime.strptime(r['date'], DEFAULT_SERVER_DATE_FORMAT)
                    r['date'] = date_move.strftime(date_format)
                    r['date_maturity'] = datetime.strptime(r['date_maturity'], DEFAULT_SERVER_DATE_FORMAT).strftime(date_format)
                    r['displayed_name'] = '-'.join(
                        r[field_name] for field_name in ('move_name', 'ref', 'name')
                        if r[field_name] not in (None, '', '/')
                    )
                    if move_matching_in_futur:
                        r['matching_number'] = '*'

                    r['report'] = False
                    if date_from_dt and date_move_dt < date_from_dt:
                        r['report'] = True

                    new_list.append(r)

            init_balance_lines = self._generate_init_balance_lines(init_account)

            line_partner[partner]['new_lines'] = init_balance_lines + new_list

        # remove unused partner
        for partner, value in line_partner.items():
            if not value['new_lines']:
                del line_partner[partner]

        # calcul des sommes par partner
        # calcul des sommes par compte
        for partner, value in line_partner.items():
            balance = 0.0
            sum_debit = 0.0
            sum_credit = 0.0
            for r in value['new_lines']:
                balance += r['debit'] - r['credit']
                r['progress'] = balance
                sum_debit += r['debit']
                sum_credit += r['credit']

                r['s_debit'] = True if round(r['debit'], 4) else False
                r['s_credit'] = True if round(r['credit'], 4) else False

                line_account[r['account_id']]['debit'] += r['debit']
                line_account[r['account_id']]['credit'] += r['credit']
                line_account[r['account_id']]['active'] = True
                line_account[r['account_id']]['balance'] += r['debit'] - r['credit']

            line_partner[partner]['debit - credit'] = sum_debit - sum_credit
            line_partner[partner]['debit'] = sum_debit
            line_partner[partner]['credit'] = sum_credit
            partner_ids.append(partner)

        # remove unused account
        for key, value in line_account.items():
            if value['active'] == False:
                del line_account[key]

        return line_partner, line_account, partner_ids

    def _lines(self, data, partner):
        return data['line_partner'][partner.id]['new_lines']

    def _sum_partner(self, data, partner, field):
        if field not in ['debit', 'credit', 'debit - credit']:
            return
        return data['line_partner'][partner.id][field]

    def _account(self, data):
        return data['line_account'].values()

    @api.multi
    def render_html(self, docis, data):
        data['reconcile_clause'], data['matching_in_futur'] = self._compute_reconcile_clause(data)

        data['computed'] = {}
        data['computed']['move_state'] = ['draft', 'posted']
        if data['form'].get('target_move', 'all') == 'posted':
            data['computed']['move_state'] = ['posted']

        accounts = self._search_account(data)
        obj_partner = self.env['res.partner']

        data['line_partner'], data['line_account'], partner_ids = self._generate_data(data, accounts)

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
            'accounts': self._account,
        }
        return self.env['report'].render('account_extra_report_partnerledger.report_partnerledger', docargs)

    def _search_account(self, data):
        result_selection = data['form'].get('result_selection', 'customer')
        if result_selection == 'supplier':
            acc_type = ['payable']
        elif result_selection == 'customer':
            acc_type = ['receivable']
        else:
            acc_type = ['payable', 'receivable']

        return self.env['account.account'].search([
            ('deprecated', '=', False),
            ('internal_type', 'in', acc_type),
            ('id', 'not in', data['form'].get('account_exclude_ids')),
        ])

    def _compute_reconcile_clause(self, data):
        reconcile_clause = ""
        list_match_in_futur = []

        if not data['form']['reconciled']:
            reconcile_clause = ' AND "account_move_line".reconciled = false '

        # dans le cas où il y a des lettrages dont la date d'un des mouvements est
        # à une date superieure à date_to, on ne peut le considérer comme lettré à date_to
        # du coup on le considère comme non lettré.
        if data['form']['rem_futur_reconciled'] and data['form']['date_to']:
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
            if list_match_in_futur and not data['form']['reconciled']:
                if len(list_match_in_futur) == 1:
                    list_match_in_futur_sql = "(%s)" %(list_match_in_futur[0])
                else:
                    list_match_in_futur_sql = str(tuple(list_match_in_futur))
                reconcile_clause = ' AND ("account_move_line".full_reconcile_id IS NULL OR "account_move_line".full_reconcile_id IN ' + list_match_in_futur_sql + ')'

        return reconcile_clause, list_match_in_futur
