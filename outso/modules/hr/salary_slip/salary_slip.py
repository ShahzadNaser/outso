# Copyright (c) 2021, The Nexperts Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import getdate, formatdate
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