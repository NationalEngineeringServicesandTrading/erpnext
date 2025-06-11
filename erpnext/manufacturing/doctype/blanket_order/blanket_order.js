// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Blanket Order', {
	onload: function(frm) {
		frm.trigger('set_tc_name_filter');

		//ADDED ON 2022-08-27
		cur_frm.call({
			"method": "nest_qcs.common.update_blanket_order_stats",
			"args": {
				"blanket_order_no": cur_frm.doc.name,
			},
			callback: function(r){
			}
		});
	},

	setup: function(frm) {
		frm.add_fetch("customer", "customer_name", "customer_name");
		frm.add_fetch("supplier", "supplier_name", "supplier_name");
		frm.get_docfield("items").allow_bulk_edit = 1; //ADDED ON 2022-08-06 
	},


	refresh: function(frm) {
		erpnext.hide_company();
		//ADDED ON 2022-08-06 *******************************************************
		frm.set_df_property("blanket_order_type", "read_only", frm.is_new() ? 0 : 1);
		//***************************************************************************
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__('View Purchase Orders'), function() {
				frappe.set_route('List', 'Purchase Order', {blanket_order: frm.doc.name});
			});
			frm.add_custom_button(__('View Sales Orders'), function() {
				frappe.set_route('List', 'Sales Order', {blanket_order: frm.doc.name});
			});
			frm.add_custom_button(__("Create Purchase Order"), function() {
				// ADDED on 2022-08-23
				new frappe.ui.form.MultiSelectDialog({
					title:"Select Call Off Order",
					doctype: "Sales Order",
					target: cur_frm,
					primary_action_label: "Create Purchase Order",  //************************************** */
					date_field: "transaction_date",
					setters: {
						company: null,
					},
					get_query() {
						return {
							query:"nest_qcs.common.get_pending_call_off_order",
							filters: {'blanket_order_no': cur_frm.doc.name}
						}
					},
					action: function(selections){ 
						if (selections.length >0) {
							cur_dialog.hide();
							//console.log('Blanket Sales Order ' + selections[0] + ' selected.')
							cur_frm.call({
								"method": "nest_qcs.common.create_call_off_purchase_order",
								"args": {
									"blanket_order_no": cur_frm.doc.name,
									"sales_order_no": selections[0]
								},
								callback: function(r){
									frappe.msgprint({
										title: __('Call-Off Purchase Order Created'),
										indicator: 'green',
										message: __('Call-Off Purchase Order ' + r.message + ' has been created. <hr>Kindly review and Submit.')
									});
									cur_frm.refresh();
								}
							});

						} else {
							frappe.throw ("Please select a Call-Off Order.");
						}
					}
				});

				// *************************  HELP HELP HELP  ****** THERE HAS TO BE A BETTER WAY!!! ******************************
				setTimeout(() => {
					// Hide Create New Purchase Order
					cur_dialog.buttons[0].getElementsByClassName('btn btn-default btn-sm btn-modal-close')[0].style.display="none";
					// Rename Primary Button
					cur_dialog.buttons[0].getElementsByClassName('btn btn-primary btn-sm')[0].innerText="Create Purchase Order";	
					// Rename the Title of the Dialog Box
					cur_dialog.header[0].children[0].getElementsByClassName('modal-title')[0].innerText = "Select Call-Off Sales Order"				
				},  2000);
				
			});//.addClass("btn-primary"); //DISABLED ON 2022-08-06

			frm.add_custom_button(__("Create Call-Off Order"), function(){
				let d = new frappe.ui.Dialog({
					title: 'Enter Call Off Order details',
					fields: [
						{
							label: 'Call Off Order Number',
							fieldname: 'co_name',
							fieldtype: 'Data'
						},
						{
							label: 'Call Off Order Date',
							fieldname: 'co_date',
							fieldtype: 'Date'
						},
						{
							label: 'Call Off Order Lines (Agreement Line No:qty1, Agreement Line No:qty2, etc)',
							fieldname: 'co_lines',
							fieldtype: 'Small Text'
						}
					],
					primary_action_label: 'Create Call Off Order',
					primary_action(values) {
						cur_frm.call({
							"method": "nest_qcs.common.validate_create_call_off_order",
							"args": {
								"values": values,
							},
							callback: function(r){
								if (r.message.error>0) {
									//console.log(r.message.message);
									frappe.msgprint({
										title: __('Error'),
										indicator: 'red',
										message: __(r.message.message)
									});
								} else {
									d.hide();
									//make_create_call_off_order(values);
									cur_frm.call({
										"method": "nest_qcs.common.make_create_call_off_order",
										"args": {
											"values": values,
											"blanket_order_no": cur_frm.doc.name
										},
										callback: function(r){
											frappe.msgprint({
												title: __('Call-Off Order Created'),
												indicator: 'green',
												message: __('Call-Off Order ' + r.message + ' has been created. <hr>Please attach the Call-Off Order to the Blanket Agreement, then review and Submit the Sales Order.')
											});
											cur_frm.refresh();
										}
									});								}
							}
						});
					}
				});
				d.show();
			});
			
			frm.add_custom_button(__("Upload XML Call-Off Order"), function(){
				new frappe.ui.FileUploader({
					doctype: cur_frm.doctype,
					docname: cur_frm.docname,
					label: 'Upload XML File',
					on_success(file_doc) {
						console.log(file_doc);
						attach_xml(file_doc);
					}
				});
			}).addClass("btn-primary");
	
		};

		//ADDED ON 2022-08-27
		cur_frm.call({
			"method": "nest_qcs.common.update_blanket_order_stats",
			"args": {
				"blanket_order_no": cur_frm.doc.name,
			},
			callback: function(r){
			}
		});

	},

	//ADDED ON 2022-08-06 *******AND MODIFIED ON 2023-03-27************************************************
	validate: function(frm) {
        if (frm.doc.__islocal) {
            switch(frm.doc.blanket_order_type) {
                case "Selling":
					if (frm.doc.agreement_type == 'LTPA') {
						frm.doc.naming_series = 'LTPA' + frm.doc.from_date.toString().substr(2,2) + "/" + frm.doc.from_date.toString().substr(5,2) + "/.###";;
						break;
					}
					else if (frm.doc.agreement_type == 'Supplier Services') {
						frm.doc.naming_series = 'SSA' + frm.doc.from_date.toString().substr(2,2) + "/" + frm.doc.from_date.toString().substr(5,2) + "/.###";;
						break;
					}
					else {
						frm.doc.naming_series = "SPA.YY./.###";
						break;	
					};
                case "Purchasing":
                    frm.doc.naming_series = "BPA.YY./.###";
                    break;
            }        
        }
    },

	selling_currency: function(frm) {
		frm.call({
			"method": "frappe.client.get_value",
			"args": {
				"doctype": "Currency Exchange",
				"filters":{ 
					"from_currency":  frm.doc.selling_currency,
					"to_currency": "AED"
				},
					fieldname: "exchange_rate"
			},
			callback: function(r){
				if (r.message.exchange_rate) {
					frm.set_value("selling_conversion_rate", r.message.exchange_rate);
				}
				else {
					frm.set_value("selling_conversion_rate", 1);
				}
				
			}
		});
	},

	buying_currency: function (frm) {
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
				}
				else {
					frm.set_value("buying_conversion_rate", 1);
				}
				
			}
		});
	},


	//***************************************************************************

	onload_post_render: function(frm) {
		frm.get_field("items").grid.set_multiple_add("item_code", "qty");
	},

	tc_name: function (frm) {
		erpnext.utils.get_terms(frm.doc.tc_name, frm.doc, function (r) {
			if (!r.exc) {
				frm.set_value("terms", r.message);
			}
		});
	},

	btc_name: function (frm) {
		erpnext.utils.get_terms(frm.doc.btc_name, frm.doc, function (r) {
			if (!r.exc) {
				frm.set_value("buying_terms", r.message);
			}
		});
	},

	set_tc_name_filter: function(frm) {
		// Setting Terms & Conditions filters.
			frm.set_query("tc_name", function() {
				return { filters: { selling: 1 } };
			});
			frm.set_query("btc_name", function() {
				return { filters: { buying: 1 } };
			});
	},

	blanket_order_type: function (frm) {
		frm.trigger('set_tc_name_filter');
	},

	// ***************  ADDED 2023-03-27 ****************************************************
	customer: function (frm) {
			frm.set_query('contact_person', 
				() => {
					return {
						query: 'frappe.contacts.doctype.contact.contact.contact_query',
						filters: {
							link_doctype: 'Customer',
							link_name: cur_frm.doc.customer
						}
					}
				}
			)
		}
	}
);

function attach_xml(file_doc){
	let fname = file_doc.name;
	let fpath = file_doc.file_url;
	console.log('Attaching XML File')
	console.log(fname);
	console.log(fpath);
	cur_frm.attachments.attachment_uploaded(file_doc);
	console.log('File Attached');
	cur_frm.call({
		"method": "nest_qcs.common.validate_call_off_order",
		"args": {
			"filename": fname,
			"filepath": fpath,
			"blanket_order_no": cur_frm.doc.name
		},
		callback: function(r){
			if (r.message.error>0  && r.message.error<=100) {
				//console.log(r.message.message);
				frappe.confirm(r.message.message + "<hr>Do you want to Proceed?",
				() => {
					// action to perform if Yes is selected
					frappe.dom.freeze(frappe.session.user_fullname.substr(0, frappe.session.user_fullname.indexOf(" ")) + ", please wait!");
					create_call_off(fpath, r.message.message);
				}, () => {
					// action to perform if No is selected
					cur_frm.attachments.remove_attachment(fname);
				})			
			}
			else if (r.message.error>100) {
				console.log(r.message.message);
				frappe.msgprint({
					title: __('Error'),
					indicator: 'red',
					message: __(r.message.message)
				});
				cur_frm.attachments.remove_attachment(fname);
			} else {
				create_call_off(fpath, '');
			}
		}
	});

}

function create_call_off(fpath, comments) {
	console.log("Creating Call off Order from " + fpath);
	cur_frm.call({
		"method": "nest_qcs.common.create_call_off_order",
		"args": {
			"filepath": fpath,
			"blanket_order_no": cur_frm.doc.name,
			"comments": comments,
			"user_email": frappe.session.user_email
		},
		callback: function(r){
			frappe.dom.unfreeze();
			frappe.msgprint({
				title: __('Call-Off Order Created'),
				indicator: 'green',
				message: __('Call-Off Order ' + r.message + ' has been created. <hr>Kindly review and Submit.')
			});
			cur_frm.refresh();
		}
	});
}

function clean_up_dialog() {
	// Hide Create New Purchase Order
	//cur_dialog.buttons[0].getElementsByClassName('btn btn-default btn-sm btn-modal-close')[0].style.display="none";
	// Rename Primary Button
	//cur_dialog.buttons[0].getElementsByClassName('btn btn-primary btn-sm')[0].innerText="Create Purchase Order";

}
