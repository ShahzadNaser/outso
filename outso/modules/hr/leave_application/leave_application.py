# Copyright (c) 2021, The Nexperts Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from erpnext.hr.doctype.leave_applicatoin.leave_application import LeaveApplication
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
					if doc.status != status:
						doc.db_set('status', status)
						doc.db_set('leave_type', self.leave_type)
						doc.db_set('leave_application', self.name)
						doc.db_set('leave_arrival_leave',1)
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
					doc.leave_arrival_leave = 1
					doc.flags.ignore_validate = True
					doc.insert(ignore_permissions=True)
					doc.submit()
