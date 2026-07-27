# Copyright (c) 2021, The Nexperts Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from erpnext.hr.doctype.leave_application.leave_application import LeaveApplication, AttendanceAlreadyMarkedError,  get_number_of_leave_days, get_leave_balance_on
from frappe.utils import getdate
from erpnext.buying.doctype.supplier_scorecard.supplier_scorecard import daterange

class CusotmLeaveApplication(LeaveApplication):
	def update_attendance(self):
		if self.status == "Approved":
			for dt in daterange(getdate(self.from_date), getdate(self.to_date)):
				date = dt.strftime("%Y-%m-%d")
				status = "Half Day" if self.half_day_date and getdate(date) == getdate(self.half_day_date) else "On Leave"
				attendance_name = frappe.db.exists('Attendance', dict(employee = self.employee,
					attendance_date = date, docstatus = ('!=', 2)))
				if attendance_name:
					# update existing attendance, change absent to on leave
					doc = frappe.get_doc('Attendance', attendance_name)
					if True or doc.status != status:
						doc.db_set('status', status)
						doc.db_set('leave_type', self.leave_type)
						doc.db_set('leave_application', self.name)
						doc.db_set('late_arrival_leave',1 if self.get("description") == "Late Arrival" else 0)
				else:
					# make new attendance and submit it
					doc = frappe.new_doc("Attendance")
					doc.employee = self.employee
					doc.employee_name = self.employee_name
					doc.attendance_date = date
					doc.company = self.company
					doc.leave_type = self.leave_type
					doc.leave_application = self.name
					doc.status = status
					doc.late_arrival_leave = 1 if self.get("description") == "Late Arrival" else 0
					doc.flags.ignore_validate = True
					doc.insert(ignore_permissions=True)
					doc.submit()
	def validate_attendance(self):
		attendance = frappe.db.sql("""select name from `tabAttendance` where employee = %s and (attendance_date between %s and %s)
					and status = "Present" and docstatus = 1""",
			(self.employee, self.from_date, self.to_date))
		if attendance and self.description != "Late Arrival":
			frappe.throw(_("Attendance for employee {0} is already marked for this day").format(self.employee),
				AttendanceAlreadyMarkedError)
	def before_save(self):
		if self.from_date and self.to_date:
			total_leave_days = get_number_of_leave_days(self.employee, self.leave_type,
				self.from_date, self.to_date, self.half_day, self.half_day_date)
			leave_balance = get_leave_balance_on(self.employee, self.leave_type, self.from_date, self.to_date,
								consider_all_leaves_in_the_allocation_period=True)

			if self.status != "Rejected" and (leave_balance < total_leave_days or not leave_balance) and not frappe.db.get_value("Leave Type",self.leave_type, "is_lwp"):
				frappe.throw(_("There is not enough leave balance for Leave Type {0}")
					.format(self.leave_type))
