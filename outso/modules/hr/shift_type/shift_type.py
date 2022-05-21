# Copyright (c) 2021, The Nexperts Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from erpnext.hr.doctype.shift_type.shift_type import ShiftType
from frappe.utils import cint
import itertools

class CusotmShiftType(ShiftType):
    @frappe.whitelist()
    def process_auto_attendance(self):
        from erpnext.hr.doctype.employee_checkin.employee_checkin import mark_attendance_and_link_log
        if not cint(self.enable_manual_attendance) or not self.process_attendance_after or not self.last_sync_of_checkin or cint(self.enable_auto_attendance):
            return

        filters = {
            'skip_auto_attendance':'0',
            'attendance':('is', 'not set'),
            'time':('>=', self.process_attendance_after),
            'shift_actual_end': ('<', self.last_sync_of_checkin),
            'shift': self.name
        }

        logs = frappe.db.get_list('Employee Checkin', fields="*", filters=filters, order_by="employee,time")
        for key, group in itertools.groupby(logs, key=lambda x: (x['employee'], x['shift_actual_start'])):
            single_shift_logs = list(group)
            attendance_status, working_hours, late_entry, early_exit, in_time, out_time = self.get_attendance(single_shift_logs)
            mark_attendance_and_link_log(single_shift_logs, attendance_status, key[1].date(), working_hours, late_entry, early_exit, in_time, out_time, self.name)
        for employee in self.get_assigned_employee(self.process_attendance_after, True):
            self.mark_absent_for_dates_with_no_attendance(employee)
