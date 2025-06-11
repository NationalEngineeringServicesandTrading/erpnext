frappe.query_reports["Employee Balances"] = {
	"filters": [
		// {
		// 	"fieldname":"company",
		// 	"label": __("Company"),
		// 	"fieldtype": "Link",
		// 	"options": "Company",
		// 	"default": frappe.defaults.get_user_default("Company"),
		// 	"reqd": 0
		// },
		{
			"fieldname":"posting_date",
			"label": __("As On Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		// {
		// 	"fieldname":"employee",
		// 	"label": __("Employee"),
		// 	"fieldtype": "Link",
		// 	"options": "Employee",
        //     "reqd": 0
		// }
	]
}
