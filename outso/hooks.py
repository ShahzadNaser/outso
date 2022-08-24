from . import __version__ as app_version

app_name = "outso"
app_title = "outso"
app_publisher = "Shahzad Naser"
app_description = "outso"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "shahzadnaser1122@gmail.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "/assets/outso/css/outso.css"
# app_include_js = "/assets/outso/js/outso.js"

# include js, css files in header of web template
web_include_css = "/assets/outso/css/outso.css"
# web_include_js = "/assets/outso/js/outso.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "outso/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Salary Slip" : "public/js/salary_slip.js",
    "Data Import" : "public/js/data_import.js",
	"Shift Type"  : "public/js/shift_type.js",
    "Material Request" : "public/js/material_request.js"
 
}
doctype_list_js = {
    "Attendance" : "public/js/attendance_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "outso.install.before_install"
# after_install = "outso.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "outso.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Shift Type": "outso.modules.hr.shift_type.shift_type.CusotmShiftType",
	"Salary Slip": "outso.modules.hr.salary_slip.salary_slip.CustomSalarySlip"
}

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
# 	"all": [
# 		"outso.tasks.all"
# 	],
# 	"daily": [
# 		"outso.tasks.daily"
# 	],
# 	"hourly": [
# 		"outso.tasks.hourly"
# 	],
# 	"weekly": [
# 		"outso.tasks.weekly"
# 	]
# 	"monthly": [
# 		"outso.tasks.monthly"
# 	]
	"cron" : {
		# run everyhour at 30 mins
		# "30 * * * *" : [
		# 	"outso.modules.hr.attendance.attendance.process_auto_attendance_for_all_shifts_custom"
		# ],
	  "*/10 * * * *" : [
			"outso.modules.hr.attendance.attendance.mark_checkins"
		]
	}
}

# Testing
# -------

# before_tests = "outso.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "outso.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "outso.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

user_data_fields = [
	{
		"doctype": "{doctype_1}",
		"filter_by": "{filter_by}",
		"redact_fields": ["{field_1}", "{field_2}"],
		"partial": 1,
	},
	{
		"doctype": "{doctype_2}",
		"filter_by": "{filter_by}",
		"partial": 1,
	},
	{
		"doctype": "{doctype_3}",
		"strict": False,
	},
	{
		"doctype": "{doctype_4}"
	}
]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"outso.auth.validate"
# ]

doctypes_list = ["Attendance", "Salary Slip", "Salary Structure Assignment", "Employee"]

fixtures = [
    {"doctype": "Client Script", "filters": [
        [
            "dt", "in", doctypes_list
        ]
    ]},
    {"doctype": "Property Setter", "filters": [
        [
            "doc_type", "in", doctypes_list
        ]
    ]},
    {"doctype": "Custom Field", "filters": [
        [
            "dt", "in", doctypes_list
        ]
    ]}
]

# from erpnext.payroll.doctype.salary_slip.salary_slip import SalarySlip
# from outso.modules.hr.salary_slip.salary_slip import get_data_for_eval

# SalarySlip.get_data_for_eval = get_data_for_eval

override_whitelisted_methods = {
	"frappe.utils.change_log.show_update_popup": "outso.api.utils.show_update_popup"
}

doc_events = {
 	"Attendance":{
		"before_save" :  "outso.modules.hr.attendance.attendance.before_save"
	},
   	"Salary Structure Assignment":{
		"before_save" :  "outso.modules.hr.salary_structure_assignment.salary_structure_assignment.before_save"
	}
}