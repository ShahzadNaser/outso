# Copyright (c) 2013, Shahzad Naser and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	data = []
	columns = [
		_("Employee") + ":Link/Employee:300", _("Earned Amount") + ":Currency/currency:160", _("Piece Rate Amount") + ":Currency/currency:180"
	]

	data = get_wo_details(filters)
	salaries = get_ssa()

	for row in data:
		row.update({"earned_amount":salaries.get(row.get("employee")) or 0})
	return columns, data


def get_wo_details(filters={}):
	from_date = frappe.utils.getdate(str(filters.get("year")) + "-" + str(filters.get("month"))+ "-01")
	to_date = frappe.utils.get_last_day(from_date)

	completed_pieces_data = frappe.db.sql('''
		SELECT 
			jctl.employee as employee,
			emp.employee_name as employee_name,
			round((pwri.rate/pwri.pieces)*sum(jctl.completed_qty),3)  as piece_rate_amount
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
		LEFT JOIN
			`tabEmployee` emp
			ON
				emp.name = jctl.employee

		WHERE 
			jctl.docstatus = 1 and jctl.to_time is not null and date(jctl.to_time) between %s and %s
		GROUP BY
			jctl.employee
	''', (from_date, to_date), as_dict=True,debug=True)

	return completed_pieces_data or []

def get_ssa():
	salaries = {}
	records = frappe.db.sql("""
		SELECT
			ssa.employee,
			ssa.base
		FROM
			`tabSalary Structure Assignment` ssa 
		WHERE 
			ssa.docstatus = 1 AND ssa.from_date = (
			SELECT 
				temp_ssa1.from_date
			FROM
				`tabSalary Structure Assignment` temp_ssa1
			WHERE
				temp_ssa1.docstatus = 1
					AND temp_ssa1.employee = ssa.employee
			ORDER BY temp_ssa1.from_date DESC
			LIMIT 1 OFFSET 0)
		""",as_dict=True)
	for row in records:
		if row.get("employee") not in salaries:
			salaries[row.get("employee")] = row.get("base")

	return salaries