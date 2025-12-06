# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _, scrub
from frappe.utils import add_days, add_to_date, flt, getdate

from erpnext.accounts.utils import get_fiscal_year


def execute(filters=None):
	return Analytics(filters).run()


class Analytics(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.date_field = (
			"transaction_date"
			if self.filters.doc_type in ["Sales Order", "Purchase Order"]
			else "posting_date"
		)
		self.months = [
			"Jan",
			"Feb",
			"Mar",
			"Apr",
			"May",
			"Jun",
			"Jul",
			"Aug",
			"Sep",
			"Oct",
			"Nov",
			"Dec",
		]
		self.get_period_date_ranges()

	def run(self):
		self.get_columns()
		self.get_data()
		self.get_chart_data()

		# Skipping total row for tree-view reports
		skip_total_row = 0

		if self.filters.tree_type in [
			"Supplier Group",
			"Item Group",
			"Customer Group",
			"Territory",
			"Order Type",
			"Cost Center",
		]:
			skip_total_row = 1

		return self.columns, self.data, None, self.chart, None, skip_total_row

	def get_columns(self):
		# ****** ADDED 2025-06-27 HUSAM *********************************/
		if self.filters.tree_type == "Brand-Sales Region":
			self.columns = [
				{
					"label": _("Brand"),
					"options": "Brand",
					"fieldname": "brand",
					"fieldtype": "Link",
					"width": 200,
				}
			]
			self.columns.append(
				{
					"label": _("Sales Region"),
					"options": "Sales Region",
					"fieldname": "sales_region",
					"fieldtype": "Link",
					"width": 140,
				}
			)
		# ****** ADDED 2025-06-27 HUSAM *********************************/

		# ****** ADDED 2023-12-12 HUSAM *********************************/
		elif (
			self.filters.tree_type == "Cost Center-Item Group"
			or self.filters.tree_type == "Cost Center-Sales Person"
		):
			self.columns = [
				{
					"label": _("Cost Center"),
					"options": "Cost Center",
					"fieldname": "cost_center",
					"fieldtype": "Link",
					"width": 140,
				}
			]
			self.columns.append(
				{
					"label": _("Item Group"),
					"options": "Item Group",
					"fieldname": "item_group",
					"fieldtype": "Link",
					"width": 200,
				}
			)
			self.columns.append(
				{
					"label": _("Sales Person"),
					"options": "Sales Person",
					"fieldname": "sales_person",
					"fieldtype": "Link",
					"width": 140,
				}
			)

		else:
			# ****** ADDED 2023-12-12 HUSAM *********************************/
			self.columns = [
				{
					"label": _(self.filters.tree_type),
					"options": self.filters.tree_type if self.filters.tree_type != "Order Type" else "",
					"fieldname": "entity",
					"fieldtype": "Link" if self.filters.tree_type != "Order Type" else "Data",
					"width": 140 if self.filters.tree_type != "Order Type" else 200,
				}
			]

		if self.filters.tree_type in ["Customer", "Supplier", "Item"]:
			self.columns.append(
				{
					"label": _(self.filters.tree_type + " Name"),
					"fieldname": "entity_name",
					"fieldtype": "Data",
					"width": 140,
				}
			)

		if self.filters.tree_type == "Item":
			self.columns.append(
				{
					"label": _("UOM"),
					"fieldname": "stock_uom",
					"fieldtype": "Link",
					"options": "UOM",
					"width": 100,
				}
			)

		for end_date in self.periodic_daterange:
			period = self.get_period(end_date)
			self.columns.append(
				{"label": _(period), "fieldname": scrub(period), "fieldtype": "Float", "width": 120}
			)

		self.columns.append(
			{"label": _("Total"), "fieldname": "total", "fieldtype": "Float", "width": 120}
		)

	def get_data(self):
		if self.filters.tree_type in ["Customer", "Supplier"]:
			self.get_sales_transactions_based_on_customers_or_suppliers()
			self.get_rows()

		elif self.filters.tree_type == "Item":
			self.get_sales_transactions_based_on_items()
			self.get_rows()

		elif self.filters.tree_type in ["Customer Group", "Supplier Group", "Territory"]:
			self.get_sales_transactions_based_on_customer_or_territory_group()
			self.get_rows_by_group()

		elif self.filters.tree_type == "Item Group":
			self.get_sales_transactions_based_on_item_group()
			self.get_rows_by_group()

		# ****** ADDED 2023-10-16 HUSAM *********************************/
		elif self.filters.tree_type == "Cost Center":
			self.get_sales_transactions_based_on_cost_center()
			self.get_rows_by_group()
		# ****** ADDED 2023-10-16 HUSAM *********************************/

		# ****** ADDED 2023-12-12 HUSAM *********************************/
		elif self.filters.tree_type == "Cost Center-Item Group":
			self.get_sales_transactions_based_on_cost_center_item_group()
			self.get_rows_by_group()
		# ****** ADDED 2023-12-12 HUSAM *********************************/

		# ****** ADDED 2023-12-23 HUSAM *********************************/
		elif self.filters.tree_type == "Cost Center-Sales Person":
			self.get_sales_transactions_based_on_cost_center_sales_person()
			self.get_rows_by_group()
		# ****** ADDED 2023-12-12 HUSAM *********************************/

		# ****** ADDED 2025-06-27 HUSAM *********************************/
		elif self.filters.tree_type == "Brand-Sales Region":
			self.get_sales_transactions_based_on_Brand_Sales_Region()
			self.get_rows_by_group()
		# ****** ADDED 2025-06-27 HUSAM *********************************/

		elif self.filters.tree_type == "Order Type":
			if self.filters.doc_type != "Sales Order":
				self.data = []
				return
			self.get_sales_transactions_based_on_order_type()
			self.get_rows_by_group()

		elif self.filters.tree_type == "Project":
			self.get_sales_transactions_based_on_project()
			self.get_rows()

	def get_sales_transactions_based_on_order_type(self):
		if self.filters["value_quantity"] == "Value":
			value_field = "base_net_total"
		else:
			value_field = "total_qty"

		self.entries = frappe.db.sql(
			""" select s.order_type as entity, s.{value_field} as value_field, s.{date_field}
			from `tab{doctype}` s where s.docstatus = 1 and s.company = %s and s.{date_field} between %s and %s
			and ifnull(s.order_type, '') != '' order by s.order_type
		""".format(
				date_field=self.date_field, value_field=value_field, doctype=self.filters.doc_type
			),
			(self.filters.company, self.filters.from_date, self.filters.to_date),
			as_dict=1,
		)

		self.get_teams()

	def get_sales_transactions_based_on_customers_or_suppliers(self):
		if self.filters["value_quantity"] == "Value":
			value_field = "base_net_total as value_field"
		else:
			value_field = "total_qty as value_field"

		if self.filters.tree_type == "Customer":
			entity = "customer as entity"
			entity_name = "customer_name as entity_name"
		else:
			entity = "supplier as entity"
			entity_name = "supplier_name as entity_name"

		self.entries = frappe.get_all(
			self.filters.doc_type,
			fields=[entity, entity_name, value_field, self.date_field],
			filters={
				"docstatus": 1,
				"company": self.filters.company,
				self.date_field: ("between", [self.filters.from_date, self.filters.to_date]),
			},
		)

		self.entity_names = {}
		for d in self.entries:
			self.entity_names.setdefault(d.entity, d.entity_name)

	def get_sales_transactions_based_on_items(self):

		if self.filters["value_quantity"] == "Value":
			value_field = "base_net_amount"
		else:
			value_field = "stock_qty"

		self.entries = frappe.db.sql(
			"""
			select i.item_code as entity, i.item_name as entity_name, i.stock_uom, i.{value_field} as value_field, s.{date_field}
			from `tab{doctype} Item` i , `tab{doctype}` s
			where s.name = i.parent and i.docstatus = 1 and s.company = %s
			and s.{date_field} between %s and %s
		""".format(
				date_field=self.date_field, value_field=value_field, doctype=self.filters.doc_type
			),
			(self.filters.company, self.filters.from_date, self.filters.to_date),
			as_dict=1,
		)

		self.entity_names = {}
		for d in self.entries:
			self.entity_names.setdefault(d.entity, d.entity_name)

	def get_sales_transactions_based_on_customer_or_territory_group(self):
		if self.filters["value_quantity"] == "Value":
			value_field = "base_net_total as value_field"
		else:
			value_field = "total_qty as value_field"

		if self.filters.tree_type == "Customer Group":
			entity_field = "customer_group as entity"
		elif self.filters.tree_type == "Supplier Group":
			entity_field = "supplier as entity"
			self.get_supplier_parent_child_map()
		else:
			entity_field = "territory as entity"

		self.entries = frappe.get_all(
			self.filters.doc_type,
			fields=[entity_field, value_field, self.date_field],
			filters={
				"docstatus": 1,
				"company": self.filters.company,
				self.date_field: ("between", [self.filters.from_date, self.filters.to_date]),
			},
		)
		self.get_groups()

	def get_sales_transactions_based_on_item_group(self):
		if self.filters["value_quantity"] == "Value":
			value_field = "base_net_amount"
		else:
			value_field = "qty"

		self.entries = frappe.db.sql(
			"""
			select i.item_group as entity, i.{value_field} as value_field, s.{date_field}
			from `tab{doctype} Item` i , `tab{doctype}` s
			where s.name = i.parent and i.docstatus = 1 and s.company = %s
			and s.{date_field} between %s and %s
		""".format(
				date_field=self.date_field, value_field=value_field, doctype=self.filters.doc_type
			),
			(self.filters.company, self.filters.from_date, self.filters.to_date),
			as_dict=1,
		)

		self.get_groups()

	# ****** ADDED 2023-10-16 HUSAM *********************************/
	def get_sales_transactions_based_on_cost_center(self):
		if self.filters["value_quantity"] == "Value":
			value_field = "base_net_amount"
		else:
			value_field = "qty"

		self.entries = frappe.db.sql(
			"""
			select i.cost_center as entity, i.{value_field} as value_field, s.{date_field}
			from `tab{doctype} Item` i , `tab{doctype}` s
			where s.name = i.parent and i.docstatus = 1 and s.company = '%s'
			and s.{date_field} between '%s' and '%s'
		""".format(
				date_field=self.date_field, value_field=value_field, doctype=self.filters.doc_type
			)
			% (self.filters.company, self.filters.from_date, self.filters.to_date),
			as_dict=1,
		)

		self.get_groups()

	# ****** ADDED 2023-10-16 HUSAM *********************************/

	# ****** ADDED 2023-12-12 HUSAM *********************************/
	def get_sales_transactions_based_on_cost_center_item_group(self):
		if self.filters["value_quantity"] == "Value":
			value_field = "base_net_amount"
		else:
			value_field = "qty"

		sql = """
			select i.cost_center as cost_center, i.item_group as item_group,
			concat(concat(i.cost_center,' / '), i.item_group) as entity,
			i.{value_field} as value_field, s.{date_field}
			from `tab{doctype} Item` i , `tab{doctype}` s
			where s.name = i.parent and i.docstatus = 1 and s.company = '%s'
			and s.{date_field} between '%s' and '%s'
		""".format(
			date_field=self.date_field, value_field=value_field, doctype=self.filters.doc_type
		) % (
			self.filters.company,
			self.filters.from_date,
			self.filters.to_date,
		)

		self.entries = frappe.db.sql(sql, as_dict=1)

		self.get_groups()

	# ****** ADDED 2023-12-12 HUSAM *********************************/

	# ****** ADDED 2023-12-23 HUSAM *********************************/
	def get_sales_transactions_based_on_cost_center_sales_person(self):
		if self.filters["value_quantity"] == "Value":
			value_field = "base_net_amount"
		else:
			value_field = "qty"

		sql = """
			select i.cost_center as cost_center, i.item_group as item_group, st.sales_person, st.allocated_percentage,
			concat(concat(concat(concat(i.cost_center,' / '), i.item_group), ' / '), ifnull(st.sales_person,"")) as entity,
			i.{value_field}*ifnull(st.allocated_percentage/100,1) as value_field, s.{date_field}
			from `tab{doctype} Item` i , `tab{doctype}` s
			left join `tabSales Team` st on s.name = st.parent
			where s.name = i.parent and i.docstatus = 1 and s.company = '%s'
			and s.{date_field} between '%s' and '%s'
		""".format(
			date_field=self.date_field, value_field=value_field, doctype=self.filters.doc_type
		) % (
			self.filters.company,
			self.filters.from_date,
			self.filters.to_date,
		)
		frappe.errprint(sql)
		self.entries = frappe.db.sql(sql, as_dict=1)

		self.get_groups()

	# ****** ADDED 2023-12-23 HUSAM *********************************/

	# ****** ADDED 2025-06-27 HUSAM *********************************/
	def get_sales_transactions_based_on_Brand_Sales_Region(self):
		if self.filters["value_quantity"] == "Value":
			value_field = "base_net_amount"
		else:
			value_field = "qty"

		sql = """
			select t.brand as brand, s.sales_region as sales_region, i.{value_field} as value_field, s.{date_field},
			concat(concat(t.brand,' / '), s.sales_region) as entity
			from `tab{doctype} Item` i inner join `tab{doctype}` s on s.name = i.parent
            left join `tabItem` t on i.item_code = t.name
			where i.docstatus = 1 and s.company = '%s'
			and s.{date_field} between '%s' and '%s'
		""".format(
			date_field=self.date_field, value_field=value_field, doctype=self.filters.doc_type
		) % (
			self.filters.company,
			self.filters.from_date,
			self.filters.to_date,
		)
		# frappe.errprint (sql)
		self.entries = frappe.db.sql(sql, as_dict=1)

		self.get_groups()

	# ****** ADDED 2025-06-27 HUSAM *********************************/

	def get_sales_transactions_based_on_project(self):
		if self.filters["value_quantity"] == "Value":
			value_field = "base_net_total as value_field"
		else:
			value_field = "total_qty as value_field"

		entity = "project as entity"

		self.entries = frappe.get_all(
			self.filters.doc_type,
			fields=[entity, value_field, self.date_field],
			filters={
				"docstatus": 1,
				"company": self.filters.company,
				"project": ["!=", ""],
				self.date_field: ("between", [self.filters.from_date, self.filters.to_date]),
			},
		)

	def get_rows(self):
		self.data = []
		self.get_periodic_data()

		for entity, period_data in self.entity_periodic_data.items():
			row = {
				"entity": entity,
				"entity_name": self.entity_names.get(entity) if hasattr(self, "entity_names") else None,
			}
			total = 0
			for end_date in self.periodic_daterange:
				period = self.get_period(end_date)
				amount = flt(period_data.get(period, 0.0))
				row[scrub(period)] = amount
				total += amount

			row["total"] = total

			if self.filters.tree_type == "Item":
				row["stock_uom"] = period_data.get("stock_uom")

			self.data.append(row)

	def get_rows_by_group(self):
		self.get_periodic_data()
		out = []

		for d in reversed(self.group_entries):
			row = {"entity": d.name, "indent": self.depth_map.get(d.name)}
			# ****** ADDED 2023-12-12 HUSAM *********************************/
			if (
				self.filters.tree_type == "Cost Center-Item Group"
				or self.filters.tree_type == "Cost Center-Sales Person"
			):
				row = {
					"entity": d.name,
					"indent": self.depth_map.get(d.name),
					"cost_center": d.cost_center,
					"item_group": d.item_group,
					"sales_person": d.sales_person,
				}
			# ****** ADDED 2023-12-12 HUSAM *********************************/

			# ****** ADDED 2025-06-27 HUSAM *********************************/
			if self.filters.tree_type == "Brand-Sales Region":
				row = {
					"entity": d.name,
					"indent": self.depth_map.get(d.name),
					"brand": d.brand,
					"sales_region": d.sales_region,
				}
			# ****** ADDED 2025-06-27 HUSAM *********************************/
			total = 0
			for end_date in self.periodic_daterange:
				period = self.get_period(end_date)
				amount = flt(self.entity_periodic_data.get(d.name, {}).get(period, 0.0))
				# if d.name is None:
				# 	pass
				# elif d.name.find('BENTLY') > 0:
				# 	frappe.errprint('*** / ' + d.name + ': ' + str(period) + ': ' + str(amount))
				row[scrub(period)] = amount
				if d.parent and (self.filters.tree_type != "Order Type" or d.parent == "Order Types"):
					self.entity_periodic_data.setdefault(d.parent, frappe._dict()).setdefault(period, 0.0)
					self.entity_periodic_data[d.parent][period] += amount
				total += amount

			row["total"] = total
			# ****** ADDED 2023-12-12&23 HUSAM *********************************/
			if (
				self.filters.tree_type == "Cost Center-Item Group"
				or self.filters.tree_type == "Cost Center-Sales Person"
			):
				if total > 0 and self.depth_map.get(d.name) > 0:
					out = [row] + out
			else:
				# ****** ADDED 2023-12-12&23 HUSAM *********************************/
				out = [row] + out

		self.data = out

	def get_periodic_data(self):
		self.entity_periodic_data = frappe._dict()

		for d in self.entries:
			if self.filters.tree_type == "Supplier Group":
				d.entity = self.parent_child_map.get(d.entity)
			period = self.get_period(d.get(self.date_field))
			self.entity_periodic_data.setdefault(d.entity, frappe._dict()).setdefault(period, 0.0)
			self.entity_periodic_data[d.entity][period] += flt(d.value_field)

			# if d.entity is None:
			# 		pass
			# elif d.entity.find('BENTLY') > 0:
			# 	frappe.errprint('entity: ' + str(d.entity) + ' / period: ' + str(period) + ' / value_field: ' + str(d.value_field))

			if self.filters.tree_type == "Item":
				self.entity_periodic_data[d.entity]["stock_uom"] = d.stock_uom

	def get_period(self, posting_date):
		if self.filters.range == "Weekly":
			period = _("Week {0} {1}").format(str(posting_date.isocalendar()[1]), str(posting_date.year))
		elif self.filters.range == "Monthly":
			period = _(str(self.months[posting_date.month - 1])) + " " + str(posting_date.year)
		elif self.filters.range == "Quarterly":
			period = _("Quarter {0} {1}").format(
				str(((posting_date.month - 1) // 3) + 1), str(posting_date.year)
			)
		else:
			year = get_fiscal_year(posting_date, company=self.filters.company)
			period = str(year[0])
		return period

	def get_period_date_ranges(self):
		from dateutil.relativedelta import MO, relativedelta

		from_date, to_date = getdate(self.filters.from_date), getdate(self.filters.to_date)

		increment = {"Monthly": 1, "Quarterly": 3, "Half-Yearly": 6, "Yearly": 12}.get(
			self.filters.range, 1
		)

		if self.filters.range in ["Monthly", "Quarterly"]:
			from_date = from_date.replace(day=1)
		elif self.filters.range == "Yearly":
			from_date = get_fiscal_year(from_date)[1]
		else:
			from_date = from_date + relativedelta(from_date, weekday=MO(-1))

		self.periodic_daterange = []
		for dummy in range(1, 53):
			if self.filters.range == "Weekly":
				period_end_date = add_days(from_date, 6)
			else:
				period_end_date = add_to_date(from_date, months=increment, days=-1)

			if period_end_date > to_date:
				period_end_date = to_date

			self.periodic_daterange.append(period_end_date)

			from_date = add_days(period_end_date, 1)
			if period_end_date == to_date:
				break

	def get_groups(self):
		if self.filters.tree_type == "Territory":
			parent = "parent_territory"
		if self.filters.tree_type == "Customer Group":
			parent = "parent_customer_group"
		if self.filters.tree_type == "Item Group":
			parent = "parent_item_group"
		if self.filters.tree_type == "Supplier Group":
			parent = "parent_supplier_group"
		# ****** ADDED 2023-10-16 HUSAM *********************************/
		if self.filters.tree_type == "Cost Center":
			parent = "parent_cost_center"
		# ****** ADDED 2023-10-16 HUSAM *********************************/

		self.depth_map = frappe._dict()

		# ****** ADDED 2023-12-12 HUSAM *********************************/
		if self.filters.tree_type == "Cost Center-Item Group":
			self.group_entries = frappe.db.sql(
				"""
					select sd.name, sd.cost_center, sd.item_group, sd.lft, sd.rgt, sd.parent, td.parent sales_person from
					(select concat(concat(cc.name,' / '), ig.name) as name, cc.name as cost_center, ig.name as item_group,
					cc.lft*1000+ig.lft as lft, cc.rgt*1000+ig.rgt as rgt ,
					concat(concat(cc.parent_cost_center, ' / '), ig.parent_item_group) as parent
					from `tabCost Center` cc, `tabItem Group` ig
					where cc.disabled = 0 and cc.company = '{company}') sd left join `tabTarget Detail` td
					on sd.cost_center = td.cost_center and sd.item_group = td.item_group
					order by sd.lft
					""".format(
					company=self.filters.company
				),
				as_dict=1,
			)
		# ****** ADDED 2025-06-27 HUSAM *********************************/
		elif self.filters.tree_type == "Brand-Sales Region":
			if self.filters["value_quantity"] == "Value":
				value_field = "base_net_amount"
			else:
				value_field = "qty"

			self.group_entries = frappe.db.sql(
				"""
				select brand, sales_region, name, parent,
				ROW_NUMBER() OVER(ORDER BY brand, sales_region)*2 as lft,
				ROW_NUMBER() OVER(ORDER BY brand, sales_region)*2+1 as rgt
				from (select brand, sales_region, entity as name, null as parent from
				(select t.brand as brand, s.sales_region as sales_region, i.{value_field} as value_field, s.{date_field},
				concat(concat(t.brand,' / '), s.sales_region) as entity
				from `tab{doctype} Item` i inner join `tab{doctype}` s on s.name = i.parent
				left join `tabItem` t on i.item_code = t.name
				where i.docstatus = 1 and s.company = '%s'
				and s.{date_field} between '%s' and '%s') r2
				group by brand, sales_region, entity ) r1
				order by brand, sales_region, lft, rgt
				""".format(
					date_field=self.date_field, value_field=value_field, doctype=self.filters.doc_type
				)
				% (self.filters.company, self.filters.from_date, self.filters.to_date),
				as_dict=1,
			)
			# select b.name as brand, sr.name as sales_region,
			# concat(concat(b.name,' / '), sr.name) as name,
			# NULL as parent,
			# ROW_NUMBER() OVER(ORDER BY b.name, sr.name)*2 as lft,
			# ROW_NUMBER() OVER(ORDER BY b.name, sr.name)*2+1 as rgt
			# from `tabBrand` b, `tabSales Region` sr
			# where b.disabled = 0 and sr.docstatus = 0
			# order by b.name, sr.name;

		# ****** ADDED 2023-12-23 HUSAM *********************************/
		elif self.filters.tree_type == "Cost Center-Sales Person":
			self.group_entries = frappe.db.sql(
				"""
					select cc.name as cost_center, ig.name as item_group, sp.sales_person as sales_person,
					concat(concat(concat(concat(cc.name,' / '), ig.name), ' / '), ifnull(sp.sales_person,"")) as name,
					cc.lft*1000+ig.lft as lft, cc.rgt*1000+ig.rgt as rgt ,
					concat(concat(cc.parent_cost_center, ' / '), ig.parent_item_group) as parent
					from `tabCost Center` cc, `tabItem Group` ig,
					(select sales_person from `tabSales Team` where parent like 'SO%' group by sales_person) sp
					where cc.disabled = 0 and cc.company = '{company}'
					order by cc.lft*1000+ig.lft;
					""".format(
					company=self.filters.company
				),
				as_dict=1,
			)
		else:
			# ****** ADDED 2023-12-12 HUSAM *********************************/
			self.group_entries = frappe.db.sql(
				"""select name, lft, rgt , {parent} as parent
				from `tab{tree}` order by lft""".format(
					tree=self.filters.tree_type, parent=parent
				),
				as_dict=1,
			)
			# ****** ADDED 2023-10-16 HUSAM *********************************/
			if self.filters.tree_type == "Cost Center":
				self.group_entries = frappe.db.sql(
					"""select name, lft, rgt , {parent} as parent
					from `tab{tree}` where disabled = 0 and company = '{company}' order by lft""".format(
						tree=self.filters.tree_type, parent=parent, company=self.filters.company
					),
					as_dict=1,
				)
			# ****** ADDED 2023-10-16 HUSAM *********************************/

		for d in self.group_entries:
			if d.parent:
				self.depth_map.setdefault(d.name, int(self.depth_map.get(d.parent) or 0) + 1)
			else:
				self.depth_map.setdefault(d.name, 0)

	def get_teams(self):
		self.depth_map = frappe._dict()

		self.group_entries = frappe.db.sql(
			""" select * from (select "Order Types" as name, 0 as lft,
			2 as rgt, '' as parent union select distinct order_type as name, 1 as lft, 1 as rgt, "Order Types" as parent
			from `tab{doctype}` where ifnull(order_type, '') != '') as b order by lft, name
		""".format(
				doctype=self.filters.doc_type
			),
			as_dict=1,
		)

		for d in self.group_entries:
			if d.parent:
				self.depth_map.setdefault(d.name, self.depth_map.get(d.parent) + 1)
			else:
				self.depth_map.setdefault(d.name, 0)

	def get_supplier_parent_child_map(self):
		self.parent_child_map = frappe._dict(
			frappe.db.sql(""" select name, supplier_group from `tabSupplier`""")
		)

	def get_chart_data(self):
		length = len(self.columns)

		if self.filters.tree_type in ["Customer", "Supplier"]:
			labels = [d.get("label") for d in self.columns[2 : length - 1]]
		elif self.filters.tree_type == "Item":
			labels = [d.get("label") for d in self.columns[3 : length - 1]]
		else:
			labels = [d.get("label") for d in self.columns[1 : length - 1]]
		self.chart = {"data": {"labels": labels, "datasets": []}, "type": "line"}

		if self.filters["value_quantity"] == "Value":
			self.chart["fieldtype"] = "Currency"
		else:
			self.chart["fieldtype"] = "Float"
