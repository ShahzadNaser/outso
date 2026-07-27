import frappe
from frappe.utils import nowdate, get_first_day, get_last_day
from outso.utils import get_post_params

@frappe.whitelist()
def get():
    error = False
    data = []
    msg = "Scuccess"
    try:
        body = get_post_params()
        data = get_attendance_details(body.get("employee"),body.get("date"))
        
    except Exception as err:
        error = True
        traceback = frappe.get_traceback()
        frappe.log_error(message=traceback , title="Error in Api")
        msg = "Something went wrong please try again."
    return {
        'data': data,
        'error': error,
        'msg': msg
    }


def get_attendance_details(employee, date=nowdate()):
    return frappe.db.sql("""
        SELECT
            sum(IF(att.status = 'Present', 1, 0)) as 'Present',
            sum(IF(att.status = 'Absent', 1, 0)) as 'Absent',
            sum(IF(att.status = 'Half Day', 1, 0)) as 'Half Day',
            sum(IF(att.leave_type = 'Leave Without Pay', (IF(att.status = 'Half Day',0.5,1)), 0)) as 'Leave Without Pay',
            sum(IF(att.leave_type = 'Annual Leave', (IF(att.status = 'Half Day',0.5,1)), 0)) as 'Annual Leave',
            sum(IF(att.leave_type = 'Casual Leave', (IF(att.status = 'Half Day',0.5,1)), 0)) as 'Casual Leave',
            sum(IF(att.leave_type = 'Sick Leave', (IF(att.status = 'Half Day',0.5,1)), 0)) as 'Sick Leave',
            sum(IF(att.leave_type = 'Leave Without Pay', (IF(att.status = 'Half Day',0.5,1)), 0)) as 'Leave Without Pay',
            sum(IF(att.late_entry = 1, 1, 0)) as 'Total Late Entry',
            sum(IF(att.early_exit = 1, 1, 0)) as 'Total Early Exit'
        FROM
            `tabAttendance` att
        WHERE
            att.employee = %s and att.docstatus = 1 and att.attendance_date between %s and %s

    """,(employee, get_first_day(date), get_last_day(date)),as_dict=True)