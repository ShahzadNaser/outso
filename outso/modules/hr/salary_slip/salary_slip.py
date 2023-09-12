# Copyright (c) 2021, The Nexperts Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
import math
from frappe.utils import getdate, formatdate, flt
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

    def calculate_variable_tax(self, payroll_period, tax_component):
        # get Tax slab from salary structure assignment for the employee and payroll period
        tax_slab = self.get_income_tax_slabs(payroll_period)

        # get remaining numbers of sub-period (period for which one salary is processed)
        remaining_sub_periods = get_period_factor(self.employee,
            self.start_date, self.end_date, self.payroll_frequency, payroll_period)[1]
        # get taxable_earnings, paid_taxes for previous period
        previous_taxable_earnings = self.get_taxable_earnings_for_prev_period(payroll_period.start_date,
            self.start_date, tax_slab.allow_tax_exemption)
        previous_total_paid_taxes = self.get_tax_paid_in_period(payroll_period.start_date, self.start_date, tax_component)

        # get taxable_earnings for current period (all days)
        current_taxable_earnings = self.get_taxable_earnings(tax_slab.allow_tax_exemption)
        future_structured_taxable_earnings = current_taxable_earnings.taxable_earnings * (math.ceil(remaining_sub_periods) - 1)

        # get taxable_earnings, addition_earnings for current actual payment days
        current_taxable_earnings_for_payment_days = self.get_taxable_earnings(tax_slab.allow_tax_exemption, based_on_payment_days=0)
        current_structured_taxable_earnings = current_taxable_earnings_for_payment_days.taxable_earnings
        current_additional_earnings = current_taxable_earnings_for_payment_days.additional_income
        current_additional_earnings_with_full_tax = current_taxable_earnings_for_payment_days.additional_income_with_full_tax

        # Get taxable unclaimed benefits
        unclaimed_taxable_benefits = 0
        if self.deduct_tax_for_unclaimed_employee_benefits:
            unclaimed_taxable_benefits = self.calculate_unclaimed_taxable_benefits(payroll_period)
            unclaimed_taxable_benefits += current_taxable_earnings_for_payment_days.flexi_benefits

        # Total exemption amount based on tax exemption declaration
        total_exemption_amount = self.get_total_exemption_amount(payroll_period, tax_slab)

        #Employee Other Incomes
        other_incomes = self.get_income_form_other_sources(payroll_period) or 0.0

        # Total taxable earnings including additional and other incomes
        total_taxable_earnings = previous_taxable_earnings + current_structured_taxable_earnings + future_structured_taxable_earnings \
            + current_additional_earnings + other_incomes + unclaimed_taxable_benefits - total_exemption_amount

        # Total taxable earnings without additional earnings with full tax
        total_taxable_earnings_without_full_tax_addl_components = total_taxable_earnings - current_additional_earnings_with_full_tax

        # Structured tax amount
        total_structured_tax_amount = self.calculate_tax_by_tax_slab(
            total_taxable_earnings_without_full_tax_addl_components, tax_slab)
        current_structured_tax_amount = (total_structured_tax_amount - previous_total_paid_taxes) / remaining_sub_periods

        # Total taxable earnings with additional earnings with full tax
        full_tax_on_additional_earnings = 0.0
        if current_additional_earnings_with_full_tax:
            total_tax_amount = self.calculate_tax_by_tax_slab(total_taxable_earnings, tax_slab)
            full_tax_on_additional_earnings = total_tax_amount - total_structured_tax_amount

        current_tax_amount = current_structured_tax_amount + full_tax_on_additional_earnings
        if flt(current_tax_amount) < 0:
            current_tax_amount = 0
        return current_tax_amount


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