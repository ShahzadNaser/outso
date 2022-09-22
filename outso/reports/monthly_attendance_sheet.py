from __future__ import unicode_literals
from calendar import monthrange
import frappe
from frappe import _, msgprint
from frappe.utils import cint, cstr, getdate

status_map = {
	"Absent": "A",
	"Half Day": "HD",
	"Holiday": "<b>H</b>",
	"Weekly Off": "<b>WO</b>",
	"On Leave": "L",
	"Present": "P",
	"Work From Home": "WFH"
	}

day_abbr = [
	"Mon",
	"Tue",
	"Wed",
	"Thu",
	"Fri",
	"Sat",
	"Sun"
]

def monthly_attendance_sheet():
    import erpnext.hr.report.monthly_attendance_sheet.monthly_attendance_sheet as original
    def _add_data(employee_map, att_map, filters, holiday_map, conditions, default_holiday_list, leave_list=None):
        record = []
        emp_att_map = {}
        for emp in employee_map:
            emp_det = employee_map.get(emp)
            if not emp_det or emp not in att_map:
                continue

            row = []
            if filters.group_by:
                row += [" "]
            row += [emp, emp_det.employee_name]

            total_p = total_a = total_l = total_h = total_um= 0.0
            emp_status_map = []
            for day in range(filters["total_days_in_month"]):
                status = None
                leave_application = None
                att_dict = att_map.get(emp).get(day + 1)

                if att_dict:
                    status = att_dict["status"]
                    leave_application = att_dict.get("leave_application")

                if status is None and holiday_map:
                    emp_holiday_list = emp_det.holiday_list if emp_det.holiday_list else default_holiday_list

                    if emp_holiday_list in holiday_map:
                        for idx, ele in enumerate(holiday_map[emp_holiday_list]):
                            if day+1 == holiday_map[emp_holiday_list][idx][0]:
                                if holiday_map[emp_holiday_list][idx][1]:
                                    status = "Weekly Off"
                                else:
                                    status = "Holiday"
                                total_h += 1

                abbr = status_map.get(status, "")
                emp_status_map.append(abbr)

                if  filters.summarized_view:
                    if status == "Present" or status == "Work From Home":
                        total_p += 1
                    elif status == "Absent":
                        total_a += 1
                    elif status == "On Leave":
                        total_l += 1
                    elif status == "Half Day":
                        total_p += 0.5
                        if leave_application:
                            total_l += 0.5
                        else:
                            total_a += 0.5
                    elif not status:
                        total_um += 1

            if not filters.summarized_view:
                row += emp_status_map

            if filters.summarized_view:
                row += [total_p, total_l, total_a, total_h, total_um]

            if not filters.get("employee"):
                filters.update({"employee": emp})
                conditions += " and employee = %(employee)s"
            elif not filters.get("employee") == emp:
                filters.update({"employee": emp})

            if filters.summarized_view:
                leave_details = frappe.db.sql("""select leave_type, status, count(*) as count from `tabAttendance`\
                    where leave_type is not NULL %s group by leave_type, status""" % conditions, filters, as_dict=1)

                time_default_counts = frappe.db.sql("""select (select count(*) from `tabAttendance` where \
                    late_entry = 1 %s) as late_entry_count, (select count(*) from tabAttendance where \
                    early_exit = 1 %s) as early_exit_count""" % (conditions, conditions), filters)

                leaves = {}
                for d in leave_details:
                    if d.status == "Half Day":
                        d.count = d.count * 0.5
                    if d.leave_type in leaves:
                        leaves[d.leave_type] += d.count
                    else:
                        leaves[d.leave_type] = d.count

                for d in leave_list:
                    if d in leaves:
                        row.append(leaves[d])
                    else:
                        row.append("0.0")

                row.extend([time_default_counts[0][0],time_default_counts[0][1]])
            emp_att_map[emp] = emp_status_map
            record.append(row)

        return record, emp_att_map
    def _get_attendance_list(conditions, filters):
        attendance_list = frappe.db.sql("""select employee, day(attendance_date) as day_of_month,
            status,leave_application from tabAttendance where docstatus = 1 %s order by employee, attendance_date""" %
            conditions, filters, as_dict=1)

        if not attendance_list:
            msgprint(_("No attendance record found"), alert=True, indicator="orange")

        att_map = {}
        for d in attendance_list:
            att_map.setdefault(d.employee, frappe._dict()).setdefault(d.day_of_month, frappe._dict({"status":"","leave_application":""}))
            att_map[d.employee][d.day_of_month] = frappe._dict({"status":d.status,"leave_application":d.leave_application})
        print("===============oooo===========oooo================")
        return att_map

    original.add_data = _add_data
    original.get_attendance_list = _get_attendance_list

def main():
    monthly_attendance_sheet()