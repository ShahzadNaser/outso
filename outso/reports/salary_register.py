from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt

import erpnext

def salary_register():
    import erpnext.payroll.report.salary_register.salary_register as original
    from erpnext.payroll.report.salary_register.salary_register import get_salary_slips, get_employee_doj_map, get_ss_ded_map

    def get_columns(salary_slips):
        """
        columns = [
            _("Salary Slip ID") + ":Link/Salary Slip:150",
            _("Employee") + ":Link/Employee:120",
            _("Employee Name") + "::140",
            _("Date of Joining") + "::80",
            _("Branch") + ":Link/Branch:120",
            _("Department") + ":Link/Department:120",
            _("Designation") + ":Link/Designation:120",
            _("Company") + ":Link/Company:120",
            _("Start Date") + "::80",
            _("End Date") + "::80",
            _("Leave Without Pay") + ":Float:130",
            _("Payment Days") + ":Float:120",
            _("Currency") + ":Link/Currency:80"
        ]
        """
        columns = [
            _("Salary Slip ID") + ":Link/Salary Slip:150",_("Employee") + ":Link/Employee:120", _("Employee Name") + "::140",
            _("Date of Joining") + "::80", _("Branch") + ":Link/Branch:-1", _("Department") + ":Link/Department:-1",
            _("Designation") + ":Link/Designation:120", _("Company") + ":Link/Company:120", _("Start Date") + "::80",
            _("End Date") + "::80", _("Leave Without Pay") + ":Float:50", _("Payment Days") + ":Float:120"
        ]

        salary_components = {_("Earning"): [], _("Deduction"): []}

        for component in frappe.db.sql("""select distinct sd.salary_component, sc.type
            from `tabSalary Detail` sd, `tabSalary Component` sc
            where sc.name=sd.salary_component and sd.amount != 0 and sd.parent in (%s)""" %
            (', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=1):
            salary_components[_(component.type)].append(component.salary_component)

        columns = columns + [(e.replace("Basic Salary","Base Salary") + ":Currency:120") for e in salary_components[_("Earning")]] + \
            [_("Salary After Absent Deductions") + ":Currency:120"] + [(d + ":Currency:120") for d in salary_components[_("Deduction")]] + \
            [_("Absent Deductions") + ":Currency:120",_("Loan Repayment") + ":Currency:120", _("Total Deduction") + ":Currency:120", _("Net Pay") + ":Currency:120"]

        return columns, salary_components[_("Earning")], salary_components[_("Deduction")]

    def get_ss_earning_map(salary_slips, currency, company_currency):
        ss_earnings = frappe.db.sql("""select sd.parent, sd.salary_component, sd.amount,sd.default_amount, ss.exchange_rate, ss.name
            from `tabSalary Detail` sd, `tabSalary Slip` ss where sd.parent=ss.name and sd.parent in (%s)""" %
            (', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=1)

        ss_earning_map = {}
        ss_gross_pay_map = {}
        for d in ss_earnings:
            if d.salary_component != "Basic Salary":
                ss_earning_map.setdefault(d.parent, frappe._dict()).setdefault(d.salary_component, 0.0)
                if currency == company_currency:
                    ss_earning_map[d.parent][d.salary_component] += flt(d.amount) * flt(d.exchange_rate if d.exchange_rate else 1)
                else:
                    ss_earning_map[d.parent][d.salary_component] += flt(d.amount)
            elif d.salary_component == "Basic Salary":
                ss_earning_map.setdefault(d.parent, frappe._dict()).setdefault(d.salary_component, 0.0)
                if currency == company_currency:
                    ss_earning_map[d.parent][d.salary_component] += flt(d.default_amount) * flt(d.exchange_rate if d.exchange_rate else 1)
                else:
                    ss_earning_map[d.parent][d.salary_component] += flt(d.default_amount)
                ss_gross_pay_map[d.parent] = {"gross_pay":flt(d.default_amount),"basic_pay":flt(d.amount)}
        return ss_earning_map, ss_gross_pay_map

    def execute(filters=None):
        if not filters: filters = {}
        currency = None
        if filters.get('currency'):
            currency = filters.get('currency')
        company_currency = erpnext.get_company_currency(filters.get("company"))
        salary_slips = get_salary_slips(filters, company_currency)
        if not salary_slips: return [], []

        columns, earning_types, ded_types = get_columns(salary_slips)
        ss_earning_map, ss_gross_pay_map = get_ss_earning_map(salary_slips, currency, company_currency)
        ss_ded_map = get_ss_ded_map(salary_slips,currency, company_currency)
        doj_map = get_employee_doj_map()
        data = []
        for ss in salary_slips:
            row = [ss.name, ss.employee, ss.employee_name, doj_map.get(ss.employee), ss.branch, ss.department, ss.designation,
                ss.company, ss.start_date, ss.end_date, ss.leave_without_pay, ss.payment_days]

            if ss.branch is not None: columns[3] = columns[3].replace('-1','120')
            if ss.department is not None: columns[4] = columns[4].replace('-1','120')
            if ss.designation is not None: columns[5] = columns[5].replace('-1','120')
            if ss.leave_without_pay is not None: columns[9] = columns[9].replace('-1','130')


            for e in earning_types:
                row.append(ss_earning_map.get(ss.name, {}).get(e))

            if currency == company_currency:
                row += [flt(ss.gross_pay) * flt(ss.exchange_rate)]
            else:
                row += [ss.gross_pay]

            for d in ded_types:
                row.append(ss_ded_map.get(ss.name, {}).get(d))

            row += [flt(ss_gross_pay_map.get(ss.name, {}).get("gross_pay") - ss_gross_pay_map.get(ss.name, {}).get("basic_pay"))]

            row.append(ss.total_loan_repayment)

            if currency == company_currency:
                row += [flt(ss.total_deduction) * flt(ss.exchange_rate), flt(ss.net_pay) * flt(ss.exchange_rate)]
            else:
                row += [ss.total_deduction, ss.net_pay]
            row.append(currency or company_currency)
            data.append(row)

        return columns, data

    original.get_columns = get_columns
    original.get_ss_earning_map = get_ss_earning_map
    original.execute = execute
    


def main():
    salary_register()