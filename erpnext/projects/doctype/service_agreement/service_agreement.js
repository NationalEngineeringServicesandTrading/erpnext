// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Service Agreement', {
	onload: function(frm) {
		frm.trigger('set_tc_name_filter');
	},
	refresh: function(frm) {
		if (frm.doc.currency) {
			frm.set_currency_labels(["total"], frm.doc.currency);
		};
		frm.add_custom_button(__('Create Call-Off Sales Orders'), function() {
			// ADDED on 2024-09-24
			let dialog = new frappe.ui.form.MultiSelectDialog({
				title:"Select Call Off Items",
				doctype: "SA On Call Support",// "Sales Order",
				target: cur_frm,
				primary_action_label: "Create Sales and Purchase Orders",  //************************************** */
				secondary_action_label: "",
				date_field: "transaction_date",
				setters: {
					item_code: null,
					item_name: null,
					rate: null,
					rate_type: null
				},
				get_query() {
					return {
						query:"nest_qcs.common.get_ssa_on_call_support_items",
						filters: {'service_agreement': cur_frm.doc.name}
					}
				},
				action: function(selections){
					if (selections.length >0) {
						cur_dialog.hide();
						cur_frm.call({
							"method": "nest_qcs.common.generate_ssa_call_off_orders",
							"args": {
								"service_agreement": cur_frm.doc.name,
								"items": selections
							},
							callback: function(r){
								frappe.msgprint({
									title: __('Call-Off Sales & Purchase Order Created'),
									indicator: 'green',
									message: __('Call-Off Sales Order ' + r.message[0] + ' and Purchase Order ' + r.message[1] + ' has been created. <hr>Kindly review and Submit.')
								});
								cur_frm.refresh();
							}
						});

					} else {
						frappe.throw ("Please select Items.");
					}
				}
			});

			// Expanding Width is Not Working!!
			dialog.$wrapper.find('.modal-content').css({
				'width': '1000px',
				'margin': '0 auto',
				'left': '50%',
				'transform': 'translateX(-50%)'
			});
		});

		frm.add_custom_button(__('Create Scheduled SO'), function() {
			frappe.prompt({
				label: 'Scheduled Date',
				fieldname: 'scheduled_date',
				fieldtype: 'Date'
			}, (values) => {
				//console.log(values.scheduled_date);
				cur_frm.call({
					"method": "nest_qcs.common.generate_ssa_sched_sales_orders",
					"args": {
						"scheduled_date": values.scheduled_date
					},
					callback: function(r){
						if (r.message.length>0) {
							frappe.msgprint({
								title: __('SSA Scheduled Sales Order(s) Created'),
								indicator: 'green',
								message: __(r.message + '<hr>Kindly review and Submit.')
							});
							cur_frm.refresh();
							cur_frm.refresh_field("billing_schedule");
						}
					}
				});

			});
		});
	},
	on_submit: function(frm){
		if(frm.doc.docstatus ==1){

			//frappe.msgprint("This got submitted");
			cur_frm.call({
				"method": "nest_qcs.common.generate_ssa_sched_purchase_orders",
				"args": {
					"service_agreement": cur_frm.doc.name
				},
				callback: function(r){
					frappe.msgprint({
						title: __('Service Agreement Master Purchase Order Created'),
						indicator: 'green',
						message: __('Master Purchase Order ' + r.message + ' has been created. <hr>Kindly review and Submit.')
					});
					cur_frm.refresh();
				}
			});

			}
	},
	currency: function(frm) {
		frm.set_currency_labels(["total"], frm.doc.currency);
		convert_selling(frm);
	},
	total: function(frm) {
		convert_selling(frm);
	},
	buying_currency: function(frm) {
		frm.set_currency_labels(["buying_total"], frm.doc.buying_currency);
		convert_buying(frm);
	},
	buying_total: function(frm) {
		convert_buying(frm);
	},

	tc_name: function (frm) {
		erpnext.utils.get_terms(frm.doc.tc_name, frm.doc, function (r) {
			if (!r.exc) {
				frm.set_value("terms", r.message);
			}
		});
	},
	set_tc_name_filter: function(frm) {
		// Setting Terms & Conditions filters.
			frm.set_query("tc_name", function() {
				return { filters: { buying: 1 } };
			});
	},
});

function convert_selling(frm) {
	frm.call({
		"method": "frappe.client.get_value",
		"args": {
			"doctype": "Currency Exchange",
			"filters":{
				"from_currency":  frm.doc.currency,
				"to_currency": "AED"
			},
				fieldname: "exchange_rate"
		},
		callback: function(r){
			if (r.message.exchange_rate) {
				frm.set_value("conversion_rate", r.message.exchange_rate);
				frm.set_value("base_total",frm.doc.total*r.message.exchange_rate);
			}
			else {
				frm.set_value("conversion_rate", 1);
				frm.set_value("base_total",frm.doc.total);
			}

		}
	});
};
function convert_buying(frm) {
	frm.call({
		"method": "frappe.client.get_value",
		"args": {
			"doctype": "Currency Exchange",
			"filters":{
				"from_currency":  frm.doc.buying_currency,
				"to_currency": "AED"
			},
				fieldname: "exchange_rate"
		},
		callback: function(r){
			if (r.message.exchange_rate) {
				frm.set_value("buying_conversion_rate", r.message.exchange_rate);
				frm.set_value("buying_base_total",frm.doc.buying_total*r.message.exchange_rate);
			}
			else {
				frm.set_value("buying_conversion_rate", 1);
				frm.set_value("buying_base_total",frm.doc.buying_total);
			}

		}
	});
};

