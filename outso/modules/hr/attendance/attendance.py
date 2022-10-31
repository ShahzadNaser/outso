# Copyright (c) 2021, The Nexperts Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import cint, flt, get_datetime, get_datetime_str
from outso.constants.globals import SHIFT_HOURS
from outso.utils import get_time_diff, get_post_params
from erpnext.hr.doctype.shift_assignment.shift_assignment import get_actual_start_end_datetime_of_shift
from erpnext.hr.doctype.employee_checkin.employee_checkin import add_log_based_on_employee_field
from datetime import timedelta
from frappe.utils.background_jobs import enqueue
from erpnext.hr.doctype.leave_application.leave_application import get_leave_balance_on
from outso.modules.hr.shift_type.shift_type import get_shift_details

import json

def before_save(doc, method):
    calculate_overtime(doc)

def calculate_overtime(doc):
    """Customization calculate overtime according to requirements"""
    if doc.working_hours and doc.working_hours > SHIFT_HOURS:

        shift_details = get_shift_details(doc.get("shift"))
        in_time = get_datetime("{0} {1}".format(doc.get("attendance_date"),shift_details.get("start_time")))
        in_time = doc.in_time if get_datetime(doc.in_time) > in_time else in_time

        temp_hours = get_time_diff(doc.out_time,in_time, "hours") - SHIFT_HOURS
        overtime_hours , rem = divmod(temp_hours,1)

        if(rem >= .50):
            if(rem >= .75):
                overtime_hours += 1
            else:
                overtime_hours += .5
        doc.overtime_hours = flt(overtime_hours)

@frappe.whitelist(allow_guest=True)
def sync_att_time(time=False):
    frappe.enqueue(method="outso.modules.hr.attendance.attendance.mark_checkins", queue="default" , timeout=1600)
    return True


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
                frappe.utils.now_datetime(),
                frappe.session.user
            ))
        except Exception as error:
            error = True
            traceback = frappe.get_traceback()
            frappe.log_error(message=traceback , title="Error in Attendance Api")
            continue

    try:
 
        frappe.db.sql("""
			INSERT INTO `tabAttendance Time`
			(`name`, `device_id`, `check_time`, `status`, `creation`, `modified`, `owner`)
			VALUES {}""".format(', '.join(['%s'] * len(insert_data))), tuple(insert_data)
        )
        frappe.db.commit()
 
    except Exception as e:
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

def mark_checkins(attendances=[]):

    if not attendances:
        attendances = frappe.db.get_list("Attendance Time", filters={"status":["!=", "Success"],"error_counter":["<",3]},order_by="check_time asc",fields=["name","device_id","check_time","error_counter"],limit=100)
    for att in attendances:
        try:
            error = False
            if not frappe.db.exists("Employee", {"attendance_device_id":att.get("device_id")}):
                frappe.db.sql("""update `tabAttendance Time` set error_counter={1} , msg = '{2}', status = '{3}', modified = '{4}' where name = '{0}' """.format(att.get("name"), att.get("error_counter")+1, "Attendance Device Id Not Found.", "Error", frappe.utils.now_datetime()))
                continue

            if not error and  att['check_time']:
                checkin = mark_employee_checktime(att['device_id'], att['check_time'], "Auto")
                frappe.db.sql("""update `tabAttendance Time` set status= '{1}' , employee_checkin = '{2}', modified = '{3}' where name = '{0}' """.format(att.get("name"), "Success", str(checkin.name), frappe.utils.now_datetime()))
                continue

        except Exception as error:
            frappe.db.sql("""update `tabAttendance Time` set error_counter={1} , msg = '{2}', status = '{3}', modified = '{4}' where name = '{0}' """.format(att.get("name"), att.get("error_counter")+1, "Server error please check error logs.", "Error", frappe.utils.now_datetime()))
            traceback = frappe.get_traceback()
            frappe.log_error(message=traceback , title=att.get("name"))
            continue
    return True
    

def mark_employee_checktime(device_id, check_time, attendance_device=None):
    _checkin_time =  frappe.utils.get_datetime(check_time)

    employee = frappe.db.exists("Employee", {"attendance_device_id":device_id},"name")

    if not employee:
        return False

    actual_shift_start, actual_shift_end, shift_details = get_actual_start_end_datetime_of_shift(employee, _checkin_time, True)

    if not frappe.db.sql(""" SELECT name from `tabEmployee Checkin` where employee = '{0}' and log_type= 'IN' and time between STR_TO_DATE('{1}', '%Y-%m-%d %H:%i:%s') and  STR_TO_DATE('{2}', '%Y-%m-%d %H:%i:%s') """.format(employee, actual_shift_start, actual_shift_end),as_list=True):
        # if there is no checkin, Add New checkin
        return add_log_based_on_employee_field(employee, _checkin_time, log_type="IN", employee_fieldname="name", device_id=attendance_device)
    else:
        next_log_type = "OUT"

        c_sql = """
            SELECT
                ec.log_type
            FROM
                `tabEmployee Checkin` ec
            WHERE
                ec.employee = '{0}'
                AND ec.shift = '{1}'
            ORDER BY `time` DESC
            LIMIT 1;
        """.format(employee, shift_details.shift_type.name)

        checkins = frappe.db.sql(c_sql, as_dict=True)
        if checkins and checkins[0]['log_type'] and checkins[0]['log_type']=="OUT":
            next_log_type = "IN"

        return add_log_based_on_employee_field(employee, _checkin_time, log_type=next_log_type, employee_fieldname="name", device_id=attendance_device)


def process_auto_attendance_for_all_shifts_custom():
    ''' Function to check latest shift to be processed and mark attendance of those shifts '''
    shift_list = frappe.db.sql("""
        SELECT 
            name,
            (case when ('%s' >= DATE_ADD(CONCAT('%s',' ',end_time),INTERVAL allow_check_out_after_shift_end_time MINUTE)) 
            THEN
                DATE_ADD(CONCAT('%s',' ',end_time),INTERVAL allow_check_out_after_shift_end_time MINUTE)
            ELSE
                DATE_ADD(CONCAT(DATE_SUB('%s', INTERVAL 1 DAY),' ',end_time),INTERVAL allow_check_out_after_shift_end_time MINUTE) 
            END)
            as shift_end
        FROM
            `tabShift Type`
        WHERE
            enable_manual_attendance = 1
        HAVING
            shift_end <= '%s' """%(frappe.utils.now(),frappe.utils.nowdate(),frappe.utils.nowdate(),frappe.utils.nowdate(),frappe.utils.now()), as_dict=True)

    for shift in shift_list:
        doc = frappe.get_doc('Shift Type', shift["name"])
        if(get_datetime(shift["shift_end"]) > doc.last_sync_of_checkin or get_datetime(shift["shift_end"]) > get_datetime(frappe.utils.now()) - timedelta(hours=1,minutes=40)):
            # doc.last_sync_of_checkin = shift["shift_end"]
            doc.last_sync_of_checkin = get_datetime_str(get_datetime(shift["shift_end"]) + timedelta(minutes=3))

            doc.save(ignore_permissions=True)
            # process_auto_attendance(doc = shift["name"], shift_end_time=shift["shift_end"])
            # frappe.enqueue(method="outso.modules.hr.attendance.attendance.process_auto_attendance", doc=shift["name"], queue="default" ,shift_end_time=shift["shift_end"] , timeout=13600)

def process_auto_attendance(doc,shift_end_time=None):
    if(not shift_end_time):
        return
    doc = frappe.get_doc('Shift Type', doc)

    if not cint(doc.enable_auto_attendance) or not shift_end_time:
        return

    doc.process_auto_attendance()

@frappe.whitelist(allow_guest=True)
def add_leaves(data):
    if isinstance(data, str):
        data = json.loads(data)
    data = frappe._dict(data)
    if not data.month:
        frappe.log_error("No Month mentioned","Auto Leave Application")
        return
    frappe.log_error("{} {}".format(data,data.get("month")),"Auto Leave Application")

    start_date = frappe.utils.get_first_day("{}-{}".format(data.get("month"),"01"))
    end_date = frappe.utils.get_last_day(start_date)
    frequencies = frappe.db.sql("""
        SELECT 
            employee, COUNT(name) AS frequency
        FROM
            `tabAttendance`
        WHERE
            docstatus = 1 AND late_entry = 1 AND attendance_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY employee
        HAVING frequency > 2;
    """,{"from_date":start_date,"to_date":end_date}, as_dict=1)
    emps = [emp.employee for emp in frequencies ]

    if not emps:
        emps = [""]
    
    att_records = frappe.db.sql("""
        SELECT 
            att.employee, att.attendance_date
        FROM
            `tabAttendance` att
        WHERE
            att.docstatus = 1 AND att.late_entry = 1  AND att.status IN ('Present', 'Absent') AND att.attendance_date BETWEEN %s AND %s AND att.employee IN %s AND att.attendance_date > IFNULL((
                SELECT 
                    temp_att.attendance_date
                FROM 
                    `tabAttendance` temp_att
                WHERE
                    temp_att.docstatus = 1 AND temp_att.late_arrival_leave = 1 AND temp_att.employee = att.employee
                ORDER BY 
                    temp_att.attendance_date DESC
                LIMIT 1 OFFSET 0),%s)
        ORDER BY employee,attendance_date ASC
    """,(start_date,end_date,emps,start_date), as_dict=1)

    employees_dict = {}
    for att in att_records:
        if att.get("employee") not in employees_dict:
            employees_dict[att.get("employee")] = [att.get("attendance_date")]
        else:
            employees_dict[att.get("employee")].append(att.get("attendance_date"))


    for i in employees_dict:
        list2 = []
        for j in range(2,len(employees_dict[i]),3):
            list2.append(employees_dict[i][j])    
        employees_dict[i] = list2

    frappe.enqueue(method="outso.modules.hr.attendance.attendance.mark_leaves", employees_dict=employees_dict, queue="default" , timeout=13600)
    # mark_leaves(employees_dict)
    return True
def mark_leaves(employees_dict={}):
    try:
        for emp in employees_dict:
            if not employees_dict[emp]:
                continue
            el = frappe.db.sql("select name from `tabLeave Application` where employee = %s and from_date between %s and %s and docstatus < 2 and description = 'Late Arrival'",(emp,frappe.utils.get_first_day(employees_dict[emp][0]),frappe.utils.get_last_day(employees_dict[emp][0])))

            if employees_dict[emp] and not el and frappe.db.get_value("Employee",emp,"employment_type") != "Piece Rate":
                for leave_date in employees_dict[emp]:
                    doc = frappe.new_doc("Leave Application")
                    doc.employee = emp
                    doc.from_date = leave_date
                    doc.to_date = leave_date
                    doc.status = "Approved"
                    doc.description = "Late Arrival"
                    doc.follow_via_email = 0
                    
                    clb  = get_leave_balance_on(emp,"Casual Leave",leave_date)
                    if clb:
                        doc.leave_type = "Casual Leave"
                    else:
                        slb  = get_leave_balance_on(emp,"Sick Leave",leave_date)
                        if slb:
                            doc.leave_type = "Sick Leave"
                        else:
                            alb  = get_leave_balance_on(emp,"Annual Leave",leave_date)
                            if alb:
                                doc.leave_type = "Annual Leave"
                            else:
                                doc.leave_type = "Leave Without Pay"
                    doc.flags.ignore_validate = True
                    doc.save(ignore_permissions=True)
                    # doc.submit()
    except Exception :
        frappe.log_error(frappe.get_traceback(),"Auto Leave Application")