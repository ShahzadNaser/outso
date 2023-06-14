# Copyright (c) 2021, The Nexperts Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import today,getdate
from outso.utils import get_post_params

@frappe.whitelist(allow_guest=True)
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

def get_op_details(item_name=None, from_date=None, to_date=None):
    if not item_name:
        return []
    items_str = ', '.join(f"'{item.name}'" for item  in frappe.db.sql("""
        SELECT name
        FROM `tabBOM`
        WHERE
            item_name LIKE %s

    """, ('%'+item_name),as_dict=True))
    print(items_str)

    cond = " AND  1=1 "

    if from_date:
        cond += " and date(jctl.from_time) >= '{}'".format(getdate(from_date))

    if to_date:
        cond += " and date(jctl.to_time) <= '{}'".format(getdate(to_date))

    operations = frappe.db.sql("""
        SELECT 
            bom.item as item_code,
            bom.item_name,
            item.image,
            jctl.employee,
            jc.work_order,
            jc.status,
            jc.operation,
            jctl.from_time,
            jctl.to_time,
            date(jctl.to_time) as completion_date, 
            sum(jctl.completed_qty) as completed_qty,
            sum(jctl.time_in_mins) as time_in_minutes
        FROM
            `tabBOM` bom
        LEFT JOIN 
                `tabItem` item
            ON
                bom.item = item.name
        LEFT JOIN 
                `tabJob Card` jc
            ON
                bom.name = jc.bom_no
        LEFT JOIN 
            `tabJob Card Time Log` jctl
            ON
                jc.name = jctl.parent
        WHERE 
            jctl.docstatus = 1 and bom.name in ({}) {}
        GROUP BY
            jctl.name

    """.format(items_str, cond),as_dict=True)

    
    return operations or []