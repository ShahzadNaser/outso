from __future__ import unicode_literals

import frappe
import os
import json
from frappe import _
from six import string_types, iteritems
from frappe.desk.query_report import get_report_doc, get_prepared_report_result, generate_report_result
def override_reports():
    # override trial balance report
    from outso.reports import monthly_attendance_sheet
    monthly_attendance_sheet.main()


@frappe.whitelist()
@frappe.read_only()
def run(report_name, filters=None, user=None, ignore_prepared_report=False, custom_columns=None):
    
    report = get_report_doc(report_name)
    if not user:
        user = frappe.session.user
    if not frappe.has_permission(report.ref_doctype, "report"):
        frappe.msgprint(
            _("Must have report permission to access this report."),
            raise_exception=True,
        )

    # custom code for overriding native reports
    override_reports()

    result = None

    if (
        report.prepared_report
        and not report.disable_prepared_report
        and not ignore_prepared_report
        and not custom_columns
    ):
        if filters:
            if isinstance(filters, string_types):
                filters = json.loads(filters)

            dn = filters.get("prepared_report_name")
            filters.pop("prepared_report_name", None)
        else:
            dn = ""
        result = get_prepared_report_result(report, filters, dn, user)
    else:
        result = generate_report_result(report, filters, user, custom_columns)

    result["add_total_row"] = report.add_total_row and not result.get(
        "skip_total_row", False
    )

    return result
