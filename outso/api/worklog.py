# Copyright (c) 2021, The Nexperts Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import today
from outso.utils import get_post_params

@frappe.whitelist()
def get():
    error = False
    data = []
    msg = "Scuccess"
    try:
        body = get_post_params()
        data = get_wo_details(body.get("employee"),body.get("from_date"),body.get("to_date"))
        
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

def get_wo_details(employee=None, from_date=today(), to_date=today()):
    if not employee:
        return []

    completed_pieces_data = frappe.db.sql('''
        SELECT 
            jctl.employee,
            jc.work_order,
            jc.operation,
            date(jctl.to_time) as completion_date, 
            sum(jctl.completed_qty) as completed_qty,
            sum(jctl.time_in_mins) as time_in_minutes
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
            date(jctl.to_time), jc.work_order,jc.operation
    ''', (from_date, to_date, employee), as_dict=True)

    return completed_pieces_data or []
