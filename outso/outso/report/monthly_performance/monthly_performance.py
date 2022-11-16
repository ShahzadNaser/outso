# Copyright (c) 2013, Shahzad Naser and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today
from frappe import _

def execute(filters=None):
	data = []
	columns = [
		_("Completion Date") + ":Date:140", _("Operation") + "::200", _("Rate") + ":Currency/currency:140", _("Finished Operations") + ":Int:160", _("Total Amount") + ":Currency/currency:180"
	]
	data = get_wo_details(filters)
	return columns, data


def get_wo_details(filters={}):
	if not filters.get("employee"):
		return []

	from_date = frappe.utils.getdate(str(filters.get("year")) + "-" + str(filters.get("month"))+ "-01")
	to_date = frappe.utils.get_last_day(from_date)

	completed_pieces_data = frappe.db.sql('''
		SELECT 
			date(jctl.to_time) as completion_date,
			jc.operation,
			round(pwri.rate/pwri.pieces,3) as rate,
			sum(jctl.completed_qty) as finished_operations,
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
	''', (from_date, to_date, filters.get("employee")), as_dict=True,debug=True)

	return completed_pieces_data or []