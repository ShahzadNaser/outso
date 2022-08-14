frappe.listview_settings['Attendance'] = {
    add_fields: ["status", "attendance_date"],
	get_indicator: function (doc) {
		if (["Present", "Work From Home"].includes(doc.status)) {
			return [__(doc.status), "green", "status,=," + doc.status];
		} else if (["Absent", "On Leave"].includes(doc.status)) {
			return [__(doc.status), "red", "status,=," + doc.status];
		} else if (doc.status == "Half Day") {
			return [__(doc.status), "orange", "status,=," + doc.status];
		}
	},
	onload: function(list_view) {
		// let me = this;
		// const months = moment().format('MMM-YYYY')+"\n"+moment().subtract(1, "month").format('MMM-YYYY');
		// list_view.page.add_inner_button(__("Add Late Arrival Leaves"), function() {
		// 	let dialog = new frappe.ui.Dialog({
		// 		title: __("Add Late Arrival Leaves"),
		// 		fields: [
		// 		{
		// 			label: __("For Month"),
		// 			fieldtype: "Select",
		// 			fieldname: "month",
		// 			options: months,
		// 			default: moment().format('MMM-YYYY'),
		// 			reqd: 1,
		// 		}],
		// 		primary_action(data) {
		// 			frappe.confirm(__('Add Leaves for month {0} ?', [data.month]), () => {
		// 				frappe.call({
		// 					method: "outso.modules.hr.attendance.attendance.add_leaves",
		// 					args: {
		// 						data: data
		// 					},
		// 					callback: function (r) {
		// 						if (r.message === 1) {
		// 							frappe.show_alert({
		// 								message: __("Add Late Arrival Leaves Added Successfully"),
		// 								indicator: 'blue'
		// 							});
		// 							cur_dialog.hide();
		// 						}
		// 					}
		// 				});
		// 			});
		// 			dialog.hide();
		// 			list_view.refresh();
		// 		},
		// 		primary_action_label: __('Add Late Arrival Leaves')

		// 	});
		// 	dialog.show();
		// });
	}
};
