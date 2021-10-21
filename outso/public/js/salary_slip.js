// Delete native function which need to be override
frappe.ui.form.handlers["Salary Slip"]["get_emp_and_working_day_details"] = [];
delete cur_frm.events["get_emp_and_working_day_details"];
delete cur_frm.cscript["get_emp_and_working_day_details"];

frappe.ui.form.on("Salary Slip", {
	get_emp_and_working_day_details: function(frm) {}
});