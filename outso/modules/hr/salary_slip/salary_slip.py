# Copyright (c) 2021, The Nexperts Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
import math
from frappe.utils import (
	cint,
	flt,
	formatdate,
	getdate,
	rounded,
)
from erpnext.payroll.doctype.payroll_period.payroll_period import get_period_factor
from erpnext.payroll.doctype.salary_slip.salary_slip import SalarySlip
import re

class CustomSalarySlip(SalarySlip):

    def get_data_for_eval(self):
        '''Returns data for evaluating formula'''
        # customization add cache for performance improvement
        #key = "temp_{0}".format(self.employee)
        #val = frappe.cache().get_value(key)
        #if val: return val

        data = frappe._dict()
        employee = frappe.get_doc("Employee", self.employee).as_dict()

        start_date = getdate(self.start_date)
        date_to_validate = (
            employee.date_of_joining
            if employee.date_of_joining > start_date
            else start_date
        )

        salary_structure_assignment = frappe.get_value(
            "Salary Structure Assignment",
            {
                "employee": self.employee,
                "salary_structure": self.salary_structure,
                "from_date": ("<=", date_to_validate),
                "docstatus": 1,
            },
            "*",
            order_by="from_date desc",
            as_dict=True,
        )

        if not salary_structure_assignment:
            frappe.throw(
                _("Please assign a Salary Structure for Employee {0} "
                "applicable from or before {1} first").format(
                    frappe.bold(self.employee_name),
                    frappe.bold(formatdate(date_to_validate)),
                )
            )

        data.update(salary_structure_assignment)
        data.update(employee)
        data.update(self.as_dict())
        self.hourly_rate = salary_structure_assignment.get("hourlyrate")

        # set values for components
        salary_components = frappe.get_all("Salary Component", fields=["salary_component_abbr","name"])
        for sc in salary_components:
            key = re.sub('[^A-Za-z0-9]+', '',sc.name.lower())
            data.setdefault(key, 0)
            data.setdefault(sc.salary_component_abbr, 0)
        
        #customization calculate and add completed pieces with rates

        completed_pieces = calculate_pieces(self)
        calculate_overtime(self)

        for piece in completed_pieces:
            key = re.sub('[^A-Za-z0-9]+', '',piece.salary_component.lower())
            data[key] = piece.amount

        for key in ('earnings', 'deductions'):
            for d in self.get(key):
                data[d.abbr] = d.amount

        # customization add data in cache for performance imporvement
        #frappe.cache().set_value(key, data, expires_in_sec=100)
        return data

    def get_taxable_earnings(self, allow_tax_exemption=False, based_on_payment_days=0):
        joining_date, relieving_date = self.get_joining_and_relieving_dates()
        taxable_earnings = 0
        additional_income = 0
        additional_income_with_full_tax = 0
        flexi_benefits = 0
        payment_days = self.get_payment_days(joining_date,relieving_date, frappe.db.get_single_value("Payroll Settings", "include_holidays_in_total_working_days"))
        for earning in self.earnings:
            if based_on_payment_days:
                amount, additional_amount = self.get_amount_based_on_payment_days(earning, joining_date, relieving_date, payment_days)
            else:
                if earning.additional_amount:
                    amount, additional_amount = earning.amount, earning.additional_amount
                else:
                    amount, additional_amount = earning.default_amount, earning.additional_amount

            if earning.is_tax_applicable:
                if earning.is_flexible_benefit:
                    flexi_benefits += amount
                else:
                    taxable_earnings += (amount - additional_amount)
                    additional_income += additional_amount

                    # Get additional amount based on future recurring additional salary
                    if additional_amount and earning.is_recurring_additional_salary:
                        additional_income += self.get_future_recurring_additional_amount(earning.additional_salary,
                            earning.additional_amount) # Used earning.additional_amount to consider the amount for the full month

                    if earning.deduct_full_tax_on_selected_payroll_date:
                        additional_income_with_full_tax += additional_amount

        if allow_tax_exemption:
            for ded in self.deductions:
                if ded.exempted_from_income_tax:
                    amount, additional_amount = ded.amount, ded.additional_amount
                    if based_on_payment_days:
                        amount, additional_amount = self.get_amount_based_on_payment_days(ded, joining_date, relieving_date)

                    taxable_earnings -= flt(amount - additional_amount)
                    additional_income -= additional_amount

                    if additional_amount and ded.is_recurring_additional_salary:
                        additional_income -= self.get_future_recurring_additional_amount(ded.additional_salary,
                            ded.additional_amount) # Used ded.additional_amount to consider the amount for the full month

        return frappe._dict({
            "taxable_earnings": taxable_earnings,
            "additional_income": additional_income,
            "additional_income_with_full_tax": additional_income_with_full_tax,
            "flexi_benefits": flexi_benefits
        })

    def get_amount_based_on_payment_days(self, row, joining_date, relieving_date, payment_days = False):
        amount, additional_amount = row.amount, row.additional_amount
        if (self.salary_structure and
            cint(row.depends_on_payment_days) and cint(self.total_working_days)
            and not (row.additional_salary and row.default_amount) # to identify overwritten additional salary
            and (not self.salary_slip_based_on_timesheet or
                getdate(self.start_date) < joining_date or
                (relieving_date and getdate(self.end_date) > relieving_date)
            )):
            additional_amount = flt((flt(row.additional_amount) * flt(payment_days or self.payment_days)
                / cint(self.total_working_days)), row.precision("additional_amount"))
            amount = flt((flt(row.default_amount) * flt(payment_days or self.payment_days)
                / cint(self.total_working_days)), row.precision("amount")) + additional_amount

        elif not self.payment_days and not self.salary_slip_based_on_timesheet and cint(row.depends_on_payment_days):
            amount, additional_amount = 0, 0
        elif not row.amount:
            amount = flt(row.default_amount) + flt(row.additional_amount)

        # apply rounding
        if frappe.get_cached_value("Salary Component", row.salary_component, "round_to_the_nearest_integer"):
            amount, additional_amount = rounded(amount), rounded(additional_amount)

        return amount, additional_amount

    def get_taxable_earnings_for_prev_period(self, start_date, end_date, allow_tax_exemption=False):
        taxable_earnings = frappe.db.sql("""
            select sum(sd.default_amount)
            from
                `tabSalary Detail` sd join `tabSalary Slip` ss on sd.parent=ss.name
            where
                sd.parentfield='earnings'
                and sd.is_tax_applicable=1
                and is_flexible_benefit=0
                and ss.docstatus=1
                and ss.employee=%(employee)s
                and ss.start_date between %(from_date)s and %(to_date)s
                and ss.end_date between %(from_date)s and %(to_date)s
            """, {
                "employee": self.employee,
                "from_date": start_date,
                "to_date": end_date
            })
        taxable_earnings = flt(taxable_earnings[0][0]) if taxable_earnings else 0

        exempted_amount = 0
        if allow_tax_exemption:
            exempted_amount = frappe.db.sql("""
                select sum(sd.amount)
                from
                    `tabSalary Detail` sd join `tabSalary Slip` ss on sd.parent=ss.name
                where
                    sd.parentfield='deductions'
                    and sd.exempted_from_income_tax=1
                    and is_flexible_benefit=0
                    and ss.docstatus=1
                    and ss.employee=%(employee)s
                    and ss.start_date between %(from_date)s and %(to_date)s
                    and ss.end_date between %(from_date)s and %(to_date)s
                """, {
                    "employee": self.employee,
                    "from_date": start_date,
                    "to_date": end_date
                })
            exempted_amount = flt(exempted_amount[0][0]) if exempted_amount else 0
        return taxable_earnings - exempted_amount



def calculate_pieces(self):
    completed_pieces_data = frappe.db.sql('''
        SELECT 
            jc.operation, pwri.salary_component, round((pwri.rate/pwri.pieces)*sum(jctl.completed_qty),3)  as amount
        FROM
                `tabPiece Work Rate Item` pwri
        LEFT JOIN 
                `tabJob Card` jc
            ON
                pwri.operation = jc.operation
        LEFT JOIN 
                `tabJob Card Time Log` jctl
            ON
                jc.name = jctl.parent
        WHERE 
            jctl.docstatus = 1 and date(jctl.to_time) between %s and %s and jctl.employee = %s
        GROUP BY
            jc.operation
    ''', (self.start_date, self.end_date, self.employee), as_dict=True)

    return completed_pieces_data

def calculate_overtime(self):
    overtime = frappe.db.sql('''
        SELECT 
            SUM(overtime_hours) as overtimehours
        FROM
            tabAttendance
        WHERE
            status = 'Present' AND docstatus = 1
                AND working_hours > 1
                AND out_time IS NOT NULL
                AND in_time IS NOT NULL
                AND attendance_date BETWEEN %s AND %s
                AND employee = %s    
    ''', (self.start_date, self.end_date, self.employee), as_dict=True)
    self.overtimehours = overtime[0].get("overtimehours") or 0