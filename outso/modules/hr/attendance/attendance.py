# Copyright (c) 2021, The Nexperts Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import flt
from outso.constants.globals import SHIFT_HOURS
from outso.utils import get_time_diff, get_post_params
from datetime import datetime
from erpnext.hr.doctype.shift_assignment.shift_assignment import get_actual_start_end_datetime_of_shift, get_employee_shift
from erpnext.hr.doctype.employee_checkin.employee_checkin import add_log_based_on_employee_field



def before_save(doc, method):
    calculate_overtime(doc)

def calculate_overtime(doc):
    '''Customization calculate overtime according to requirements'''
    if doc.working_hours and doc.working_hours > SHIFT_HOURS:
        temp_hours = get_time_diff(doc.out_time,doc.in_time, "hours") - SHIFT_HOURS
        overtime_hours , rem = divmod(temp_hours,1)
        if(rem >= .50):
            if(rem >= .75):
                overtime_hours += 1
            else:
                overtime_hours += .5
        doc.overtime_hours = flt(overtime_hours)


@frappe.whitelist(allow_guest=True)
def sync(attendance=[]):
    error = False

    if attendance:
        body = attendance
    else:
        body = get_post_params()

    insert_data = []
    for att in body['attendance_list']:
        try:
            insert_data.append((
			    frappe.generate_hash("", 10),
                att.get("employee_id"),
                frappe.utils.get_datetime(att.get("check_time")),
                "Pending",
                frappe.utils.now_datetime(),
                frappe.session.user
            ))
        except Exception as error:
            error = True
            traceback = frappe.get_traceback()
            frappe.log_error(message=traceback , title="Error in Attendance Api")
            continue

    try:
 
        frappe.db.sql('''
			INSERT INTO `tabAttendance Time`
			(`name`, `employee`, `check_time`, `status`, `creation`, `owner`)
			VALUES {}'''.format(', '.join(['%s'] * len(insert_data))), tuple(insert_data)
        )
        frappe.db.commit()
 
    except Exception as error:
        error = True
        traceback = frappe.get_traceback()
        frappe.log_error(message=traceback , title="Error in Attendance Api")
    msg = "Attendance Data Synced Successfully."
    if error:
        msg = "Something went wrong check attendance time logs."
        
    response = {
        'message': msg,
        'error': error
    }

    return response

def sync_checkin(attendance=[]):
    errors = []
    successes = []
    if attendance:
        body = attendance
    else:
        body = get_post_params()

    for att in body['attendance_list']:
        try:
            _temp_dict = att
            if not frappe.db.exists("Employee", att['employee_id']):
                # add error response
                _temp_dict["reason"] = "Employee not found or eligible for attendance."
                errors.append(_temp_dict)
                continue

            if att['check_time']:
                att = mark_employee_checktime(att['employee_id'], att['check_time'], att['attendance_device'])
                _temp_dict["checkin"] = str(att.name)
                _temp_dict["reason"] = "Done"
            successes.append(_temp_dict)
        except Exception as error:
            _temp_dict["reason"] = str(error)
            errors.append(_temp_dict)
            traceback = frappe.get_traceback()
            frappe.log_error(message=traceback , title="Error in Attendance Api")
            continue

    response = {
        'message': 'Attendance synced.',
        'errors': errors,
        'successes': successes
    }

    return response

def mark_employee_checktime(employee, check_time, attendance_device=None):
    _checkin_time = datetime.strptime(check_time, "%Y-%m-%d %H:%M:%S")
    actual_shift_start, actual_shift_end, shift_details = get_actual_start_end_datetime_of_shift(employee, _checkin_time, True)

    cin_filters = {
        "employee": employee,
        "log_type": "IN",
        'time':('between', [shift_details.actual_start, shift_details.actual_end])
    }

    if not frappe.db.get_list("Employee Checkin", cin_filters):
        # if there is no checkin, Add New checkin
        return add_log_based_on_employee_field(employee, _checkin_time, log_type="IN", employee_fieldname="name", device_id=attendance_device)
    else:
        next_log_type = "OUT"

        c_sql = """
        SELECT
            ec.*
        FROM
            `tabEmployee Checkin` ec
        WHERE
            ec.employee = '{0}'
            AND ec.shift = '{1}'
        ORDER BY `time` DESC
        LIMIT 1;
        """.format(employee, shift_details.shift_type.name)

        checkins = frappe.db.sql(c_sql, as_dict=True)
        if len(checkins) and checkins[0]['log_type'] and checkins[0]['log_type']=="OUT":
            next_log_type = "IN"

        return add_log_based_on_employee_field(employee, _checkin_time, log_type=next_log_type, employee_fieldname="name", device_id=attendance_device)
