frappe.ui.form.handlers["Material Request"]["get_items_from_bom"] = [];
delete cur_frm.events["get_items_from_bom"];
delete cur_frm.cscript["get_items_from_bom"];
frappe.ui.form.on('Material Request', {
	get_items_from_bom: function(frm) {
		var d = new frappe.ui.Dialog({
			title: __("Get Items from BOM"),
			fields: [
				{"fieldname":"bom", "fieldtype":"Link", "label":__("BOM"),
					options:"BOM", reqd: 1, get_query: function() {
						return {filters: { docstatus:1 }};
					}},
				{"fieldname":"warehouse", "fieldtype":"Link", "label":__("For Warehouse"),
					options:"Warehouse"},
				{"fieldname":"qty", "fieldtype":"Float", "label":__("Quantity"),
					reqd: 1, "default": 1},
				{"fieldname":"fetch_exploded", "fieldtype":"Check",
					"label":__("Fetch exploded BOM (including sub-assemblies)"), "default":1}
			],
			primary_action_label: 'Get Items',
			primary_action(values) {
				if(!values) return;
				values["company"] = frm.doc.company;
				if(!frm.doc.company) frappe.throw(__("Company field is required"));
				frappe.call({
					method: "erpnext.manufacturing.doctype.bom.bom.get_bom_items",
					args: values,
					callback: function(r) {
						if (!r.message) {
							frappe.throw(__("BOM does not contain any stock item"));
						} else {
							erpnext.utils.remove_empty_first_row(frm, "items");
							$.each(r.message, function(i, item) {
								var d = frappe.model.add_child(cur_frm.doc, "Material Request Item", "items");
								d.item_code = item.item_code;
								d.item_name = item.item_name;
								d.description = item.description;
                                d.warehouse = values.warehouse || item.default_warehouse;
								d.uom = item.stock_uom;
								d.stock_uom = item.stock_uom;
								d.conversion_factor = 1;
								d.qty = item.qty;
								d.project = item.project;
							});
						}
						d.hide();
						refresh_field("items");
					}
				});
			}
		});

		d.show();
	}
});