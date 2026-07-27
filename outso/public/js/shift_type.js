frappe.ui.form.on('Shift Type', {
	refresh: function(frm) {
        'Sync Checkins',
		frm.add_custom_button(__('Sync Checkins'), function(){
            frappe.call({
                 method: "outso.modules.hr.attendance.attendance.sync_att_time",
                 callback: function(r){
                      if(!r.exc) {
                        frappe.msgprint(__("Check-ins are syncing."));
                      }
                 }
            });
       });
	}
});
