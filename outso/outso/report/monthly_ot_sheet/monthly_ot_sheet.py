# Copyright (c) 2013, Shahzad Naser and contributors
# For license information, please see license.txt


from __future__ import unicode_literals

from calendar import monthrange

import frappe
from frappe import _, msgprint
from frappe.utils import cint, cstr, getdate,flt
from erpnext import get_default_company

day_abbr = [
	"Mon",
	"Tue",
	"Wed",
	"Thu",
	"Fri",
	"Sat",
	"Sun"
]

def execute(filters=None):
	if not filters: filters = {}

	if filters.hide_year_field == 1:
		filters.year = 2020

	conditions, filters = get_conditions(filters)
	columns, days = get_columns(filters)
	att_map = get_attendance_list(conditions, filters)

	if not att_map:
		return columns, []


	emp_map = get_employee_details(filters.get("group_by"), filters.get("employee"))
	holiday_list = [emp_map[d]["holiday_list"] for d in emp_map if emp_map[d]["holiday_list"]]


	default_holiday_list = frappe.get_cached_value('Company',  get_default_company(),  "default_holiday_list")
	holiday_list.append(default_holiday_list)
	holiday_list = list(set(holiday_list))
	holiday_map = get_holiday(holiday_list, filters.get("month"),filters.get("year"))

	data = []

	leave_list = None


	record, emp_att_map = add_data(emp_map, att_map, filters, holiday_map, conditions, default_holiday_list, leave_list=leave_list)
	data += record

	return columns, data


def add_data(employee_map, att_map, filters, holiday_map, conditions, default_holiday_list, leave_list=None):

	record = []
	emp_att_map = {}
	for emp in employee_map:
		emp_det = employee_map.get(emp)
		print(emp, emp_det, att_map)
		print("=============emp, emp_det, att_map=================")
		if not emp_det or emp not in att_map:
			continue

		row = []
		row += [emp, emp_det.employee_name, emp_det.designation, emp_det.department, emp_det.branch]

		total_um= 0.0
		ot_map = []
		if filters.summarized_view:
			for month in ["January","February","March","April","May","June","July","August","September","October","November","December"]:
				status = 0
				status = flt(att_map.get(emp).get(month) or 0)

				ot_map.append(status)
				total_um += flt(status or 0)
		else:
			for day in range(filters["total_days_in_month"]):
				status = 0
				status = att_map.get(emp).get(day + 1)

				if not filters.summarized_view and status is None and holiday_map:
					emp_holiday_list = emp_det.holiday_list if emp_det.holiday_list else default_holiday_list
					print(holiday_map)
					if emp_holiday_list in holiday_map:
						for idx, ele in enumerate(holiday_map[emp_holiday_list]):
							if day+1 == holiday_map[emp_holiday_list][idx][0]:
								if holiday_map[emp_holiday_list][idx][1]:
									status = "Weekly Off"
								else:
									status = "Holiday"

				ot_map.append(status or 0)
				total_um += flt(status or 0)

		row += ot_map
		row += [total_um]

		emp_att_map[emp] = ot_map
		record.append(row)

	return record, emp_att_map

def get_columns(filters):

	columns = []

	columns += [
		_("Employee") + ":Link/Employee:180", _("Employee Name") + "::120", _("Designation") + "::120", _("Department") + "::160", _("Branch") + "::140"
	]
	days = []
	for day in range(filters["total_days_in_month"]):
		date = str(filters.year) + "-" + str(filters.month)+ "-" + str(day+1)
		day_name = day_abbr[getdate(date).weekday()]
		days.append(cstr(day+1)+ " " +day_name +"::100")
	if filters.summarized_view:
		columns += ["January::120","February::120","March::120","April::120","May::120","June::120","July::120","August::120","September::120","October::120","November::120","December::120"]
	else:
		columns += days
     
	columns += [_("Total OT") + ":Float:80"]

	return columns, days

def get_attendance_list(conditions, filters):
	if not filters.summarized_view:
		attendance_list = frappe.db.sql("""select employee, day(attendance_date) as day_of_month,
			overtime_hours from tabAttendance where docstatus = 1 %s order by employee, attendance_date""" %
			conditions, filters, as_dict=1)
	else:
		attendance_list = frappe.db.sql("""select employee,monthname(attendance_date) as day_of_month, round(sum(overtime_hours),2) as
			overtime_hours from tabAttendance where docstatus = 1 %s  group by employee, day_of_month order by employee""" %
			conditions, filters, as_dict=1)

	if not attendance_list:
		msgprint(_("No attendance record found"), alert=True, indicator="orange")

	att_map = {}
	for d in attendance_list:
		att_map.setdefault(d.employee, frappe._dict()).setdefault(d.day_of_month, 0)
		att_map[d.employee][d.day_of_month] = d.overtime_hours

	return att_map

def get_conditions(filters):
	if not (filters.get("month") and filters.get("year")):
		msgprint(_("Please select month and year"), raise_exception=1)

	filters["total_days_in_month"] = monthrange(cint(filters.year), cint(filters.month))[1]

	if filters.summarized_view:
		conditions = " and year(attendance_date) = %(year)s"
	else:
		conditions = " and month(attendance_date) = %(month)s and year(attendance_date) = %(year)s"

	if filters.get("employee"): conditions += " and employee = %(employee)s"

	return conditions, filters

def get_employee_details(group_by, employee):
	emp_map = {}
	cond = ""

	if employee:
		cond = " where name = '{}' ".format(employee)

	query = """select name, employee_name, designation, department, branch, company,
		holiday_list from `tabEmployee` {}""".format(cond)

	if group_by:
		group_by = group_by.lower()
		query += " order by " + group_by + " ASC"

	employee_details = frappe.db.sql(query , as_dict=1)

	group_by_parameters = []
	if group_by:

		group_by_parameters = list(set(detail.get(group_by, "") for detail in employee_details if detail.get(group_by, "")))
		for parameter in group_by_parameters:
				emp_map[parameter] = {}


	for d in employee_details:
		if group_by and len(group_by_parameters):
			if d.get(group_by, None):

				emp_map[d.get(group_by)][d.name] = d
		else:
			emp_map[d.name] = d

	if not group_by:
		return emp_map
	else:
		return emp_map, group_by_parameters

def get_holiday(holiday_list, month, year):
	holiday_map = frappe._dict()
	for d in holiday_list:
		if d:
			holiday_map.setdefault(d, frappe.db.sql('''select day(holiday_date), weekly_off from `tabHoliday`
				where parent=%s and month(holiday_date)=%s and year(holiday_date)=%s ''', (d, month, year)))

	return holiday_map

@frappe.whitelist()
def get_attendance_years():
	year_list = frappe.db.sql_list("""select distinct YEAR(attendance_date) from tabAttendance ORDER BY YEAR(attendance_date) DESC""")
	if not year_list:
		year_list = [getdate().year]

	return "\n".join(str(year) for year in year_list)
