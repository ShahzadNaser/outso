# Copyright (c) 2021, The Nexperts Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from erpnext.hr.doctype.shift_type.shift_type import ShiftType
from frappe.utils import cint, add_months, today ,format_date
import itertools

class CusotmShiftType(ShiftType):
    @frappe.whitelist()
    def process_auto_attendance(self):
        from erpnext.hr.doctype.employee_checkin.employee_checkin import mark_attendance_and_link_log
        if not cint(self.enable_manual_attendance) or not self.process_attendance_after or not self.last_sync_of_checkin or cint(self.enable_auto_attendance):
            return
        frappe.log_error("Skip_auto_attendance:0")
        filters = {
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


        # frappe.enqueue(method="outso.modules.hr.attendance.attendance.add_leaves", data={"month":format_date(add_months(today(), -1),"YYYY-MM")}, queue="default" , timeout=13600)
        frappe.enqueue(method="outso.modules.hr.attendance.attendance.add_leaves", data={"month":format_date(today(),"YYYY-MM")}, queue="default" , timeout=13600)

    def before_save(self):
        frappe.cache().hdel(self.name, "config")

def get_shift_details(shift=None):
    if not shift:
        return False
    _config = frappe.cache().hget(shift, "config")
    if not _config:
        _config = frappe.get_doc('Shift Type',shift)
        frappe.cache().hdel(shift, "config")
        frappe.cache().hset(shift, "config", _config)
    return _config or {}

