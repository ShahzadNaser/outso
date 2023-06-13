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
        data = get_op_details(body.get("product_name"),body.get("from_date"),body.get("to_date"))
        
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

def get_op_details(item_name=None, from_date=today(), to_date=today()):
    if not item_name:
        return []
    items = [item.name for item in frappe.db.sql("""
        SELECT name
        FROM `tabBOM`
        WHERE
            item_name LIKE %s

    """, ('%'+item_name),as_dict=True)]

    operations = frappe.db.sql("""
        SELECT 
            bom.item as item_code,
            bom.item_name,
            jctl.employee,
            jc.work_order,
            jc.operation,
            date(jctl.to_time) as completion_date, 
            sum(jctl.completed_qty) as completed_qty,
            sum(jctl.time_in_mins) as time_in_minutes
        FROM
            `tabBOM` bom
        LEFT JOIN 
                `tabJob Card` jc
            ON
                bom.name = jc.bom_no
        LEFT JOIN 
            `tabJob Card Time Log` jctl
            ON
                jc.name = jctl.parent
        WHERE 
            jctl.docstatus = 1 and jctl.to_time is not null and bom.name in (%s)
        GROUP BY
            date(jctl.to_time), jc.work_order,jc.operation

    """ % (','.join(['%s'] *len(items))), items,as_dict=True)

    
    return operations or []