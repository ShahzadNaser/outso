# Copyright (c) 2013, Shahzad Naser and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today
from frappe import _

def execute(filters=None):
	data = []
	columns = [
		_("Employee") + ":Link/Employee:330",_("Time Log") + ":Date:140", _("Operation") + "::200", _("Rate") + ":Currency/currency:140", _("Finished Pieces") + ":Int:160", _("Total Amount") + ":Currency/currency:180"
	]
	data = get_wo_details(filters)
	return columns, data


def get_wo_details(filters={}):
	if not filters.get("employee"):
		return []
	employee_name = frappe.db.get_value("Employee",filters.get("employee"),"employee_name")
	from_date = frappe.utils.getdate(str(filters.get("year")) + "-" + str(filters.get("month"))+ "-01")
	to_date = frappe.utils.get_last_day(from_date)

	completed_pieces_data = frappe.db.sql('''
		SELECT 
			%s as employee,
			%s as employee_name,
			date(jctl.to_time) as time_log,
			jc.operation,
			round(pwri.rate/pwri.pieces,3) as rate,
			sum(jctl.completed_qty) as finished_pieces,
			round((pwri.rate/pwri.pieces)*sum(jctl.completed_qty),3)  as total_amount
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
			jctl.docstatus = 1 and jctl.to_time is not null and date(jctl.to_time) between %s and %s and jctl.employee = %s
		GROUP BY
			date(jctl.to_time),jc.operation
	''', (filters.get("employee"), employee_name, from_date, to_date, filters.get("employee")), as_dict=True)

	return completed_pieces_data or []