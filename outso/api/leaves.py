import frappe
from frappe.utils import today, nowdate
from outso.utils import get_post_params
from erpnext.hr.doctype.leave_application.leave_application import get_leave_allocation_records, get_leave_balance_on, get_leaves_for_period, get_pending_leaves_for_period

@frappe.whitelist()
def get():
    error = False
    data = []
    msg = "Scuccess"
    try:
        body = get_post_params()
        data = get_leave_details(body.get("employee"),body.get("date"))
        
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


@frappe.whitelist()
def get_leave_details(employee, date=nowdate()):
	allocation_records = get_leave_allocation_records(employee, date)
	leave_allocation = {}
	for d in allocation_records:
		allocation = allocation_records.get(d, frappe._dict())

		total_allocated_leaves = frappe.db.get_value('Leave Allocation', {
			'from_date': ('<=', date),
			'to_date': ('>=', date),
			'employee': employee,
			'leave_type': allocation.leave_type,
		}, 'SUM(total_leaves_allocated)') or 0

		remaining_leaves = get_leave_balance_on(employee, d, date, to_date = allocation.to_date,
			consider_all_leaves_in_the_allocation_period=True)

		end_date = allocation.to_date
		leaves_taken = get_leaves_for_period(employee, d, allocation.from_date, end_date) * -1
		leaves_pending = get_pending_leaves_for_period(employee, d, allocation.from_date, end_date)

		leave_allocation[d] = {
			"total_leaves": total_allocated_leaves,
			"expired_leaves": total_allocated_leaves - (remaining_leaves + leaves_taken),
			"leaves_taken": leaves_taken,
			"pending_leaves": leaves_pending,
			"remaining_leaves": remaining_leaves}

	ret = {
		'leave_allocation': leave_allocation,
	}

	return ret