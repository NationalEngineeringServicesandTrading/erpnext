from frappe import _


def get_data():
	return {
		"fieldname": "service_agreement",
		"non_standard_fieldnames": {"Project": "name"},
		"transactions": [
			{"label": _("Sales"), "items": ["Sales Order", "Delivery Note", "Sales Invoice"]},
			{"label": _("Purchase"), "items": ["Purchase Order", "Purchase Receipt", "Purchase Invoice"]},
			{"label": _("Bank Guarantee"), "items": ["Bank Guarantee"]},
			{"label": _("Project"), "items": ["Project"]},
			{"label": _("Blanket Order"), "items": ["Blanket Order"]},
			{"label": _("Insurance"), "items": ["Insurance"]},
		],
	}
