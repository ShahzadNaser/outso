frappe.ui.form.on('Data Import', { 
    refresh(frm) {
        cur_frm.fields_dict["reference_doctype"].get_query= function(frm) {
			return {
				filters: {
					name: ['in', ["Piece Work Rates"].concat(frappe.boot.user.can_import)]
				}
			}            
        }
    } 
});