# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from email_reply_parser import EmailReplyParser
from frappe import _, qb
from frappe.desk.reportview import get_match_cond
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Count, CurDate, Date, Sum, UnixTimestamp
from frappe.utils import add_days, flt, get_datetime, get_link_to_form, get_time, get_url, nowtime, today
from frappe.utils.user import is_website_user

from erpnext import get_default_company
from erpnext.controllers.queries import get_filters_cond
from erpnext.controllers.website_list_for_contact import get_customers_suppliers
from erpnext.setup.doctype.holiday_list.holiday_list import is_holiday
import json
from frappe.model.mapper import get_mapped_doc

class Project(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from erpnext.projects.doctype.project_user.project_user import ProjectUser
		from erpnext.projects.doctype.table_project_attachment_links.table_project_attachment_links import TableProjectAttachmentLinks
		from frappe.types import DF

		actual_end_date: DF.Date | None
		actual_start_date: DF.Date | None
		actual_time: DF.Float
		collect_progress: DF.Check
		company: DF.Link | None
		completed_at: DF.Date | None
		copied_from: DF.Data | None
		cost_center: DF.Link | None
		current_step: DF.Int
		custom_flow_name: DF.Link | None
		custom_project_name: DF.Link | None
		customer: DF.Link | None
		daily_time_to_send: DF.Time | None
		day_to_send: DF.Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
		department: DF.Link | None
		estimated_costing: DF.Currency
		expected_end_date: DF.Date | None
		expected_start_date: DF.Date | None
		first_email: DF.Time | None
		flow_step: DF.Int
		flow_template: DF.Link
		frequency: DF.Literal["Hourly", "Twice Daily", "Daily", "Weekly"]
		from_time: DF.Time | None
		gross_margin: DF.Currency
		holiday_list: DF.Link | None
		is_active: DF.Literal["Yes", "No"]
		message: DF.Text | None
		naming_series: DF.Literal["PROJ-.####"]
		notes: DF.TextEditor | None
		per_gross_margin: DF.Percent
		percent_complete: DF.Percent
		percent_complete_method: DF.Literal["Manual", "Task Completion", "Task Progress", "Task Weight"]
		priority: DF.Literal["Medium", "Low", "High"]
		project_name: DF.Data
		project_template: DF.Link | None
		project_type: DF.Link | None
		sales_order: DF.Link | None
		second_email: DF.Time | None
		started_at: DF.Datetime | None
		started_by: DF.Link | None
		status: DF.Literal["Open", "Completed", "Cancelled", "Overdue", "Overdue Completed", "Due Soon"]
		subject: DF.Data | None
		table_vics: DF.Table[TableProjectAttachmentLinks]
		test: DF.Autocomplete | None
		to_time: DF.Time | None
		total_billable_amount: DF.Currency
		total_billed_amount: DF.Currency
		total_consumed_material_cost: DF.Currency
		total_costing_amount: DF.Currency
		total_purchase_cost: DF.Currency
		total_sales_amount: DF.Currency
		users: DF.Table[ProjectUser]
		weekly_time_to_send: DF.Time | None
	# end: auto-generated types

	def onload(self):
		self.set_onload(
			"activity_summary",
			frappe.db.sql(
				"""select activity_type,
			sum(hours) as total_hours
			from `tabTimesheet Detail` where project=%s and docstatus < 2 group by activity_type
			order by total_hours desc""",
				self.name,
				as_dict=True,
			),
		)

	def before_print(self, settings=None):
		self.onload()

	def validate(self):
		if not self.is_new():
			self.copy_from_template()  # nosemgrep
		self.send_welcome_email()
		self.update_costing()
		self.update_percent_complete()
		self.validate_from_to_dates("expected_start_date", "expected_end_date")
		self.validate_from_to_dates("actual_start_date", "actual_end_date")

	def copy_from_template(self):  # nosemgrep
		"""
		Copy tasks from template
		"""
		if self.project_template and not frappe.db.get_all("Task", dict(project=self.name), limit=1):
			# has a template, and no loaded tasks, so lets create
			if not self.expected_start_date:
				# project starts today
				self.expected_start_date = today()

			template = frappe.get_doc("Project Template", self.project_template)

			if not self.project_type:
				self.project_type = template.project_type

			# create tasks from template
			project_tasks = []
			tmp_task_details = []
			for task in template.tasks:
				template_task_details = frappe.get_doc("Task", task.task)
				tmp_task_details.append(template_task_details)
				task = self.create_task_from_template(template_task_details)
				project_tasks.append(task)

			self.dependency_mapping(tmp_task_details, project_tasks)

	def create_task_from_template(self, task_details):
		return frappe.get_doc(
			dict(
				doctype="Task",
				subject=task_details.subject,
				project=self.name,
				status="Open",
				exp_start_date=self.calculate_start_date(task_details),
				exp_end_date=self.calculate_end_date(task_details),
				description=task_details.description,
				task_weight=task_details.task_weight,
				type=task_details.type,
				issue=task_details.issue,
				is_group=task_details.is_group,
				color=task_details.color,
				template_task=task_details.name,
				priority=task_details.priority,
			)
		).insert()

	def calculate_start_date(self, task_details):
		self.start_date = add_days(self.expected_start_date, task_details.start)
		self.start_date = self.update_if_holiday(self.start_date)
		return self.start_date

	def calculate_end_date(self, task_details):
		self.end_date = add_days(self.start_date, task_details.duration)
		return self.update_if_holiday(self.end_date)

	def update_if_holiday(self, date):
		holiday_list = self.holiday_list or get_holiday_list(self.company)
		while is_holiday(holiday_list, date):
			date = add_days(date, 1)
		return date

	def dependency_mapping(self, template_tasks, project_tasks):
		for project_task in project_tasks:
			template_task = frappe.get_doc("Task", project_task.template_task)

			self.check_depends_on_value(template_task, project_task, project_tasks)
			self.check_for_parent_tasks(template_task, project_task, project_tasks)

	def check_depends_on_value(self, template_task, project_task, project_tasks):
		if template_task.get("depends_on") and not project_task.get("depends_on"):
			project_template_map = {pt.template_task: pt for pt in project_tasks}

			for child_task in template_task.get("depends_on"):
				if project_template_map and project_template_map.get(child_task.task):
					project_task.reload()  # reload, as it might have been updated in the previous iteration
					project_task.append(
						"depends_on", {"task": project_template_map.get(child_task.task).name}
					)
					project_task.save()

	def check_for_parent_tasks(self, template_task, project_task, project_tasks):
		if template_task.get("parent_task") and not project_task.get("parent_task"):
			for pt in project_tasks:
				if pt.template_task == template_task.parent_task:
					project_task.parent_task = pt.name
					project_task.save()
					break

	def is_row_updated(self, row, existing_task_data, fields):
		if self.get("__islocal") or not existing_task_data:
			return True

		d = existing_task_data.get(row.task_id, {})

		for field in fields:
			if row.get(field) != d.get(field):
				return True

	def update_project(self):
		"""Called externally by Task"""
		self.update_percent_complete()
		self.update_costing()
		self.db_update()

	# 删除 Task Flow时，删除 Task Flow Step
	def after_delete(self):
		print("删除 Task Flow时，删除 Task Flow Step",self.name)
		frappe.db.delete("Task Flow Step", {"flow_name": self.name})

	def after_insert(self):
		self.create_task_flow_step()
		self.copy_from_template()  # nosemgrep
		if self.sales_order:
			frappe.db.set_value("Sales Order", self.sales_order, "project", self.name)

	def on_trash(self):
		frappe.db.set_value("Sales Order", {"project": self.name}, "project", "")

	def update_percent_complete(self):
		if self.status == "Completed":
			if (
				len(frappe.get_all("Task", dict(project=self.name))) == 0
			):  # A project without tasks should be able to complete
				self.percent_complete_method = "Manual"
				self.percent_complete = 100

		if self.percent_complete_method == "Manual":
			if self.status == "Completed":
				self.percent_complete = 100
			return

		total = frappe.db.count("Task", dict(project=self.name))

		if not total:
			self.percent_complete = 0
		else:
			if (self.percent_complete_method == "Task Completion" and total > 0) or (
				not self.percent_complete_method and total > 0
			):
				completed = frappe.db.sql(
					"""select count(name) from tabTask where
					project=%s and status in ('Cancelled', 'Completed')""",
					self.name,
				)[0][0]
				self.percent_complete = flt(flt(completed) / total * 100, 2)

			if self.percent_complete_method == "Task Progress" and total > 0:
				progress = frappe.db.sql(
					"""select sum(progress) from tabTask where
					project=%s""",
					self.name,
				)[0][0]
				self.percent_complete = flt(flt(progress) / total, 2)

			if self.percent_complete_method == "Task Weight" and total > 0:
				weight_sum = frappe.db.sql(
					"""select sum(task_weight) from tabTask where
					project=%s""",
					self.name,
				)[0][0]
				weighted_progress = frappe.db.sql(
					"""select progress, task_weight from tabTask where
					project=%s""",
					self.name,
					as_dict=1,
				)
				pct_complete = 0
				for row in weighted_progress:
					pct_complete += row["progress"] * frappe.utils.safe_div(row["task_weight"], weight_sum)
				self.percent_complete = flt(flt(pct_complete), 2)

		# don't update status if it is cancelled
		if self.status == "Cancelled":
			return

		self.status = "Completed" if self.percent_complete == 100 else "Open"

	def update_costing(self):
		from frappe.query_builder.functions import Max, Min, Sum

		TimesheetDetail = frappe.qb.DocType("Timesheet Detail")
		from_time_sheet = (
			frappe.qb.from_(TimesheetDetail)
			.select(
				Sum(TimesheetDetail.costing_amount).as_("costing_amount"),
				Sum(TimesheetDetail.billing_amount).as_("billing_amount"),
				Min(TimesheetDetail.from_time).as_("start_date"),
				Max(TimesheetDetail.to_time).as_("end_date"),
				Sum(TimesheetDetail.hours).as_("time"),
			)
			.where((TimesheetDetail.project == self.name) & (TimesheetDetail.docstatus == 1))
		).run(as_dict=True)[0]

		self.actual_start_date = from_time_sheet.start_date
		self.actual_end_date = from_time_sheet.end_date

		self.total_costing_amount = from_time_sheet.costing_amount
		self.total_billable_amount = from_time_sheet.billing_amount
		self.actual_time = from_time_sheet.time

		self.update_purchase_costing()
		self.update_sales_amount()
		self.update_billed_amount()
		self.calculate_gross_margin()

	def calculate_gross_margin(self):
		expense_amount = (
			flt(self.total_costing_amount)
			+ flt(self.total_purchase_cost)
			+ flt(self.get("total_consumed_material_cost", 0))
		)

		self.gross_margin = flt(self.total_billed_amount) - expense_amount
		if self.total_billed_amount:
			self.per_gross_margin = (self.gross_margin / flt(self.total_billed_amount)) * 100

	def update_purchase_costing(self):
		total_purchase_cost = calculate_total_purchase_cost(self.name)
		self.total_purchase_cost = total_purchase_cost and total_purchase_cost[0][0] or 0

	def update_sales_amount(self):
		total_sales_amount = frappe.db.sql(
			"""select sum(base_net_total)
			from `tabSales Order` where project = %s and docstatus=1""",
			self.name,
		)

		self.total_sales_amount = total_sales_amount and total_sales_amount[0][0] or 0

	def update_billed_amount(self):
		self.total_billed_amount = self.get_billed_amount_from_parent() + self.get_billed_amount_from_child()

	def get_billed_amount_from_parent(self):
		total_billed_amount = frappe.db.sql(
			"""select sum(base_net_amount)
			from `tabSales Invoice` si join `tabSales Invoice Item` si_item on si_item.parent = si.name
				where si_item.project is null
				and si.project is not null
				and si.project = %s
				and si.docstatus = 1""",
			self.name,
		)

		return total_billed_amount and total_billed_amount[0][0] or 0

	def get_billed_amount_from_child(self):
		total_billed_amount = frappe.db.sql(
			"""select sum(base_net_amount)
			from `tabSales Invoice Item`
				where project = %s
				and docstatus = 1""",
			self.name,
		)

		return total_billed_amount and total_billed_amount[0][0] or 0

	def after_rename(self, old_name, new_name, merge=False):
		if old_name == self.copied_from:
			frappe.db.set_value("Project", new_name, "copied_from", new_name)

	def send_welcome_email(self):
		label = f"{self.project_name} ({self.name})"
		url = get_link_to_form(self.doctype, self.name, label)

		content = "<p>{}</p>".format(
			_("You have been invited to collaborate on the project: {0}").format(url)
		)

		for user in self.users:
			if user.welcome_email_sent == 0:
				frappe.sendmail(
					user.user,
					subject=_("Project Collaboration Invitation"),
					content=content,
				)
				user.welcome_email_sent = 1

	def create_task_flow_step(self):
		if not self.flow_template:
			# print("没有模板，跳过创建步骤")  # noqa: RUF003
			return

		try:
			# 注意 Flow Templates 的 DocType 名称
			template = frappe.get_doc("Flow Templates", self.flow_template)
		except frappe.DoesNotExistError:
			frappe.throw(f"Flow Template '{self.flow_template}' 不存在")

		# 开始日期
		started_at = today()
		for step in template.steps:
			due_date = add_days(started_at, step.default_days) if step.default_days else started_at
			# print(f"Creating step: {step.label}, template_step_index: {step.idx}")
			# 完成日期 等于 开始日期 加上 默认天数
			# completed_at = add_days(started_at, step.default_days) if step.default_days else None

			# 准备插入的文档数据
			step_data = {
				"doctype": "Task Flow Step",
				"flow_name": self.name,
				"template_step_index": step.idx,
				"step_label": step.label,
				"started_at": started_at,
				"target_doctype": step.target_doctype,
				"allow_skip": step.allow_skip,
				"require_action": step.require_action,
				"assigned_to": step.user_full_name,
				"default_days": step.default_days,
				"allow_multiple": step.allow_multiple,
				"due_date": due_date,
				"description": step.description,
				"attachment_mandatory": step.attachment_mandatory
			}

			# 只有当 assigned_to 不为空且是一个有效的用户时才设置
			if hasattr(step, "assigned_to") and step.assigned_to:
				# 检查是否是完整的用户邮箱（链接字段需要的值）还是全名（显示值）  # noqa: RUF003
				if "@" in step.assigned_to or step.assigned_to in ["Administrator", "Guest"]:
					# 这是正确的用户ID，直接使用  # noqa: RUF003
					step_data["assigned_to"] = step.assigned_to
				else:
					# 如果是全名，尝试查找对应的用户ID  # noqa: RUF003
					user_id = frappe.db.get_value("User", {"full_name": step.assigned_to}, "name")
					if user_id:
						step_data["assigned_to"] = user_id
					# 如果找不到对应的用户ID，则不设置 assigned_to 字段  # noqa: RUF003

			# 只有当 assigned_by_role 存在且有效时才设置
			if hasattr(step, "assigned_by_role") and step.assigned_by_role:
				step_data["assigned_by_role"] = step.assigned_by_role

			frappe.get_doc(step_data).insert(ignore_permissions=True)

			started_at = due_date  # 下一个步骤的开始日期为当前步骤的完成日期

		# 更新 Task Flow 状态
		self.db_set(
			{
				"current_step": 1,
				"status": "Open",
				"started_by": frappe.session.user,
				"started_at": frappe.utils.now_datetime(),
			}
		)

def get_timeline_data(doctype: str, name: str) -> dict[int, int]:
	"""Return timeline for attendance"""

	timesheet_detail = frappe.qb.DocType("Timesheet Detail")

	return dict(
		frappe.qb.from_(timesheet_detail)
		.select(UnixTimestamp(timesheet_detail.from_time), Count("*"))
		.where(timesheet_detail.project == name)
		.where(timesheet_detail.from_time > CurDate() - Interval(years=1))
		.where(timesheet_detail.docstatus < 2)
		.groupby(Date(timesheet_detail.from_time))
		.run()
	)


def get_project_list(doctype, txt, filters, limit_start, limit_page_length=20, order_by="modified"):
	customers, suppliers = get_customers_suppliers("Project", frappe.session.user)

	ignore_permissions = False
	if is_website_user() and frappe.session.user != "Guest":
		if not filters:
			filters = []

		if customers:
			filters.append([doctype, "customer", "in", customers])
			ignore_permissions = True

	meta = frappe.get_meta(doctype)

	fields = "distinct *"

	or_filters = []

	if txt:
		if meta.search_fields:
			for f in meta.get_search_fields():
				if f == "name" or meta.get_field(f).fieldtype in (
					"Data",
					"Text",
					"Small Text",
					"Text Editor",
					"select",
				):
					or_filters.append([doctype, f, "like", "%" + txt + "%"])
		else:
			if isinstance(filters, dict):
				filters["name"] = ("like", "%" + txt + "%")
			else:
				filters.append([doctype, "name", "like", "%" + txt + "%"])

	return frappe.get_list(
		doctype,
		fields=fields,
		filters=filters,
		or_filters=or_filters,
		limit_start=limit_start,
		limit_page_length=limit_page_length,
		order_by=order_by,
		ignore_permissions=ignore_permissions,
	)


def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context

	list_context = get_list_context(context)
	list_context.update(
		{
			"show_sidebar": True,
			"show_search": True,
			"no_breadcrumbs": True,
			"title": _("Projects"),
			"get_list": get_project_list,
			"row_template": "templates/includes/projects/project_row.html",
		}
	)

	return list_context


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_users_for_project(doctype, txt, searchfield, start, page_len, filters):
	conditions = []
	return frappe.db.sql(
		"""select name, concat_ws(' ', first_name, middle_name, last_name)
		from `tabUser`
		where enabled=1
			and name not in ("Guest", "Administrator")
			and ({key} like %(txt)s
				or full_name like %(txt)s)
			{fcond} {mcond}
		order by
			(case when locate(%(_txt)s, name) > 0 then locate(%(_txt)s, name) else 99999 end),
			(case when locate(%(_txt)s, full_name) > 0 then locate(%(_txt)s, full_name) else 99999 end),
			idx desc,
			name, full_name
		limit %(page_len)s offset %(start)s""".format(
			**{
				"key": searchfield,
				"fcond": get_filters_cond(doctype, filters, conditions),
				"mcond": get_match_cond(doctype),
			}
		),
		{"txt": "%%%s%%" % txt, "_txt": txt.replace("%", ""), "start": start, "page_len": page_len},
	)


@frappe.whitelist()
def get_cost_center_name(project):
	return frappe.db.get_value("Project", project, "cost_center")


def hourly_reminder():
	fields = ["from_time", "to_time"]
	projects = get_projects_for_collect_progress("Hourly", fields)

	for project in projects:
		if get_time(nowtime()) >= get_time(project.from_time) or get_time(nowtime()) <= get_time(
			project.to_time
		):
			send_project_update_email_to_users(project.name)


def project_status_update_reminder():
	daily_reminder()
	twice_daily_reminder()
	weekly_reminder()


def daily_reminder():
	fields = ["daily_time_to_send"]
	projects = get_projects_for_collect_progress("Daily", fields)

	for project in projects:
		if allow_to_make_project_update(project.name, project.get("daily_time_to_send"), "Daily"):
			send_project_update_email_to_users(project.name)


def twice_daily_reminder():
	fields = ["first_email", "second_email"]
	projects = get_projects_for_collect_progress("Twice Daily", fields)
	fields.remove("name")

	for project in projects:
		for d in fields:
			if allow_to_make_project_update(project.name, project.get(d), "Twicely"):
				send_project_update_email_to_users(project.name)


def weekly_reminder():
	fields = ["day_to_send", "weekly_time_to_send"]
	projects = get_projects_for_collect_progress("Weekly", fields)

	current_day = get_datetime().strftime("%A")
	for project in projects:
		if current_day != project.day_to_send:
			continue

		if allow_to_make_project_update(project.name, project.get("weekly_time_to_send"), "Weekly"):
			send_project_update_email_to_users(project.name)


def allow_to_make_project_update(project, time, frequency):
	data = frappe.db.sql(
		""" SELECT name from `tabProject Update`
		WHERE project = %s and date = %s """,
		(project, today()),
	)

	# len(data) > 1 condition is checked for twicely frequency
	if data and (frequency in ["Daily", "Weekly"] or len(data) > 1):
		return False

	if get_time(nowtime()) >= get_time(time):
		return True


@frappe.whitelist()
def create_duplicate_project(prev_doc, project_name):
	"""Create duplicate project based on the old project"""
	import json

	prev_doc = json.loads(prev_doc)

	if project_name == prev_doc.get("name"):
		frappe.throw(_("Use a name that is different from previous project name"))

	# change the copied doc name to new project name
	project = frappe.copy_doc(prev_doc)
	project.name = project_name
	project.project_template = ""
	project.project_name = project_name
	project.insert()

	# fetch all the task linked with the old project
	task_list = frappe.get_all("Task", filters={"project": prev_doc.get("name")}, fields=["name"])

	# Create duplicate task for all the task
	for task in task_list:
		task = frappe.get_doc("Task", task)
		new_task = frappe.copy_doc(task)
		new_task.project = project.name
		new_task.insert()

	project.db_set("project_template", prev_doc.get("project_template"))


def get_projects_for_collect_progress(frequency, fields):
	fields.extend(["name"])

	return frappe.get_all(
		"Project",
		fields=fields,
		filters={"collect_progress": 1, "frequency": frequency, "status": "Open"},
	)


def send_project_update_email_to_users(project):
	doc = frappe.get_doc("Project", project)

	if is_holiday(doc.holiday_list) or not doc.users:
		return

	project_update = frappe.get_doc(
		{
			"doctype": "Project Update",
			"project": project,
			"sent": 0,
			"date": today(),
			"time": nowtime(),
			"naming_series": "UPDATE-.project.-.YY.MM.DD.-",
		}
	).insert()

	incoming_email_account = frappe.db.get_value(
		"Email Account", dict(enable_incoming=1, default_incoming=1), "email_id"
	)

	frappe.sendmail(
		recipients=get_users_email(doc),
		message=doc.message,
		subject=doc.subject,
		reference_doctype=project_update.doctype,
		reference_name=project_update.name,
		reply_to=incoming_email_account,
	)


def collect_project_status():
	for data in frappe.get_all("Project Update", {"date": today(), "sent": 0}):
		replies = frappe.get_all(
			"Communication",
			fields=["content", "text_content", "sender"],
			filters=dict(
				reference_doctype="Project Update",
				reference_name=data.name,
				communication_type="Communication",
				sent_or_received="Received",
			),
			order_by="creation asc",
		)

		for d in replies:
			doc = frappe.get_doc("Project Update", data.name)
			user_data = frappe.db.get_values(
				"User", {"email": d.sender}, ["full_name", "user_image", "name"], as_dict=True
			)[0]

			doc.append(
				"users",
				{
					"user": user_data.name,
					"full_name": user_data.full_name,
					"image": user_data.user_image,
					"project_status": frappe.utils.md_to_html(
						EmailReplyParser.parse_reply(d.text_content) or d.content
					),
				},
			)

			doc.save(ignore_permissions=True)


def send_project_status_email_to_users():
	yesterday = add_days(today(), -1)

	for d in frappe.get_all("Project Update", {"date": yesterday, "sent": 0}):
		doc = frappe.get_doc("Project Update", d.name)

		project_doc = frappe.get_doc("Project", doc.project)

		args = {"users": doc.users, "title": _("Project Summary for {0}").format(yesterday)}

		frappe.sendmail(
			recipients=get_users_email(project_doc),
			template="daily_project_summary",
			args=args,
			subject=_("Daily Project Summary for {0}").format(d.name),
			reference_doctype="Project Update",
			reference_name=d.name,
		)

		doc.db_set("sent", 1)


def update_project_sales_billing():
	sales_update_frequency = frappe.db.get_single_value("Selling Settings", "sales_update_frequency")
	if sales_update_frequency == "Each Transaction":
		return
	elif sales_update_frequency == "Monthly" and frappe.utils.now_datetime().day != 1:
		return

	# Else simply fallback to Daily
	for project in frappe.get_all("Project", filters={"status": ["!=", "Cancelled"]}):
		frappe.get_doc("Project", project.name).save()


@frappe.whitelist()
def create_kanban_board_if_not_exists(project):
	from frappe.desk.doctype.kanban_board.kanban_board import quick_kanban_board

	project = frappe.get_doc("Project", project)
	if not frappe.db.exists("Kanban Board", project.project_name):
		quick_kanban_board("Task", project.project_name, "status", project.name)

	return True


@frappe.whitelist()
def set_project_status(project, status):
	"""
	set status for project and all related tasks
	"""
	if status not in ("Completed", "Cancelled"):
		frappe.throw(_("Status must be Cancelled or Completed"))

	project = frappe.get_doc("Project", project)
	frappe.has_permission(doc=project, throw=True)

	for task in frappe.get_all("Task", dict(project=project.name)):
		frappe.db.set_value("Task", task.name, "status", status)

	project.status = status
	project.save()


def get_holiday_list(company=None):
	if not company:
		company = get_default_company() or frappe.get_all("Company")[0].name

	holiday_list = frappe.get_cached_value("Company", company, "default_holiday_list")
	if not holiday_list:
		frappe.throw(
			_("Please set a default Holiday List for Company {0}").format(frappe.bold(get_default_company()))
		)
	return holiday_list


def get_users_email(doc):
	return [d.email for d in doc.users if frappe.db.get_value("User", d.user, "enabled")]


def calculate_total_purchase_cost(project: str | None = None):
	if project:
		pitem = qb.DocType("Purchase Invoice Item")
		total_purchase_cost = (
			qb.from_(pitem)
			.select(Sum(pitem.base_net_amount))
			.where((pitem.project == project) & (pitem.docstatus == 1))
			.run(as_list=True)
		)
		return total_purchase_cost
	return None


@frappe.whitelist()
def update_costing_and_billing(project: str | None = None):
	project = frappe.get_doc("Project", project)
	project.update_costing()
	project.db_update()






# 跳过步骤
@frappe.whitelist()
def skip_task_flow_step(flow_name, template_step_index):
	"""
	跳过指定的 Task Flow 步骤
	Args:
	    flow_name (str): Task Flow name
	    template_step_index (int): Task Flow Step template_step_index
	"""
	# 将参数转换为整数
	template_step_index = int(template_step_index)

	# 获取当前步骤
	step = frappe.get_all(
		"Task Flow Step",
		filters={"flow_name": flow_name, "template_step_index": template_step_index},
		fields=["name", "allow_skip", "status", "target_doctype", "assigned_to"],
	)

	if not step:
		frappe.throw(f"Task Flow Step template_step_index={template_step_index} 不存在")

	step = step[0]

	# 检查是否允许跳过
	if not step.get("allow_skip"):
		frappe.throw(f"步骤 {template_step_index} 不允许跳过")

	if step.get("status") == "Completed":
		frappe.throw("该步骤已完成，无法跳过")

	if step.get("status") == "Skipped":
		frappe.throw("该步骤已被跳过")

	# 检查权限：确保当前用户有权执行此操作
	if step.get("assigned_to") and step["assigned_to"] != frappe.session.user:
		# 如果不是指派用户，检查用户角色是否允许执行此操作
		allowed_roles = ["System Manager", "Administrator"]
		user_roles = frappe.get_roles(frappe.session.user)
		if not any(role in allowed_roles for role in user_roles):
			frappe.throw("您没有权限执行此操作")

	# 检查前置步骤是否已完成或被跳过（确保流程顺序）
	if template_step_index > 1:
		prev_step_status = frappe.get_all(
			"Task Flow Step",
			filters={"flow_name": flow_name, "template_step_index": template_step_index - 1},
			fields=["status"],
		)

		# if prev_step_status:
		#     prev_status = prev_step_status[0]["status"]
		#     # 前置步骤必须是完成状态或跳过状态才能跳过当前步骤
		#     if prev_status not in ['Completed', 'Skipped']:
		#         frappe.throw(f"前置步骤 {template_step_index - 1} 尚未完成或跳过，不能跳过当前步骤")

	# 标记为已跳过
	frappe.db.set_value(
		"Task Flow Step",
		step["name"],
		{
			"status": "Skipped",
			"completed_at": frappe.utils.now(),  # 设置完成时间为当前时间，以便后续步骤可以继续
		},
	)

	# 强制清除缓存以确保状态立即更新
	frappe.db.commit()
	frappe.clear_cache(doctype="Task Flow Step")

	return {"message": "步骤已跳过"}


# 取消跳过指定的 Task Flow 步骤
@frappe.whitelist()
def unskip_task_flow_step(flow_name, template_step_index):
	"""
	取消跳过指定的 Task Flow 步骤
	Args:
	    flow_name (str): Task Flow name
	    template_step_index (int): Task Flow Step template_step_index
	"""
	# 将参数转换为整数
	template_step_index = int(template_step_index)

	# 获取当前步骤
	step = frappe.get_all(
		"Task Flow Step",
		filters={"flow_name": flow_name, "template_step_index": template_step_index},
		fields=["name", "allow_skip", "status", "assigned_to"],
	)

	if not step:
		frappe.throw(f"Task Flow Step template_step_index={template_step_index} 不存在")

	step = step[0]

	# 检查是否允许跳过/取消跳过（虽然取消跳过不限制此字段，但保持一致性）
	if not step.get("allow_skip"):
		frappe.throw(f"步骤 {template_step_index} 不允许跳过/取消跳过")

	if step.get("status") != "Skipped":
		frappe.throw("该步骤未被跳过，无法取消跳过")

	# 检查权限：确保当前用户有权执行此操作
	if step.get("assigned_to") and step["assigned_to"] != frappe.session.user:
		# 如果不是指派用户，检查用户角色是否允许执行此操作
		allowed_roles = ["System Manager", "Administrator"]
		user_roles = frappe.get_roles(frappe.session.user)
		if not any(role in allowed_roles for role in user_roles):
			frappe.throw("您没有权限执行此操作")

	# 检查当前步骤之后的步骤是否存在已完成的步骤（只检查已完成，不检查跳过）
	next_step_index = template_step_index + 1
	next_step = frappe.get_all(
		"Task Flow Step",
		filters={"flow_name": flow_name, "template_step_index": next_step_index},
		fields=["status"],
	)

	if next_step and next_step[0].get("status") == "Completed":
		frappe.throw(f"不允许取消跳过，因为第 {next_step_index} 步已经完成")

	# 检查当前步骤之后的其他步骤是否已完成（遍历所有后续步骤）
	total_steps = frappe.get_all(
		"Task Flow Step",
		filters={"flow_name": flow_name},
		fields=["template_step_index"],
		order_by="template_step_index desc",
		limit=1,
	)

	if total_steps:
		max_step_index = total_steps[0].template_step_index
		for check_index in range(next_step_index + 1, max_step_index + 1):
			check_step = frappe.get_all(
				"Task Flow Step",
				filters={"flow_name": flow_name, "template_step_index": check_index},
				fields=["status"],
			)
			if check_step and check_step[0].get("status") == "Completed":
				frappe.throw(f"不允许取消跳过，因为第 {check_index} 步已经完成")

	# 取消跳过状态
	frappe.db.set_value(
		"Task Flow Step",
		step["name"],
		{
			"status": "Assigned",  # 恢复为已指派状态
			"completed_at": None,  # 清除完成时间
		},
	)

	# 强制清除缓存以确保状态立即更新
	frappe.db.commit()
	frappe.clear_cache(doctype="Task Flow Step")

	return {"message": "步骤跳过已取消"}


# 验证用户是否有权限执行流程操作
@frappe.whitelist()
def validate_flow_action_permission(flow_name, step_index, user=None):
	"""
	验证用户是否有权限执行流程操作
	"""
	# 将参数转换为整数
	step_index = int(step_index)

	if not user:
		user = frappe.session.user

	try:
		# 查询对应的Task Flow Step记录
		step = frappe.get_doc("Task Flow Step", {"flow_name": flow_name, "template_step_index": step_index})

		if not step:
			return {"valid": False, "error": f"未找到步骤 {step_index} 的配置信息"}

		# 检查用户权限
		# 1. 检查用户是否是被指派的用户
		if step.assigned_to and step.assigned_to != user:
			# 检查用户角色是否允许执行此操作
			allowed_roles = ["System Manager", "Administrator"]
			user_roles = frappe.get_roles(user)
			if not any(role in allowed_roles for role in user_roles):
				return {"valid": False, "error": f"你没有权限执行此操作。该步骤指派给了 {step.assigned_to}"}

		# 2. 检查步骤状态
		if step.status == "Completed":
			return {"valid": False, "error": "该步骤已完成，无法再次执行操作"}

		# 3. 检查流程整体状态
		flow = frappe.get_doc("Project", flow_name)
		if flow.status == "Completed":
			return {"valid": False, "error": "整个流程已完成，无法执行操作"}

		# 4. 检查前置步骤是否已完成或被跳过（确保流程顺序）
		if step_index > 1:
			prev_step_status = frappe.get_all(
				"Task Flow Step",
				filters={"flow_name": flow_name, "template_step_index": step_index - 1},
				fields=["status"],
			)

			if prev_step_status:
				prev_status = prev_step_status[0]["status"]
				# 前置步骤必须是完成状态或跳过状态才能操作当前步骤
				if prev_status not in ["Completed", "Skipped"]:
					return {
						"valid": False,
						"error": f"前置步骤 {step_index - 1} 尚未完成或跳过，不能操作当前步骤",
					}

		return {"valid": True, "message": "权限验证通过"}

	except Exception as e:
		frappe.log_error(f"权限验证错误: {str(e)}")
		return {"valid": False, "error": f"权限验证过程中出现错误: {str(e)}"}
	"""
    验证用户是否有权限执行流程操作
    """
	# 将参数转换为整数
	step_index = int(step_index)

	try:
		# 查询对应的Task Flow Step记录
		step = frappe.get_doc("Task Flow Step", {"flow_name": flow_name, "template_step_index": step_index})

		if not step:
			return {"valid": False, "error": f"未找到步骤 {step_index} 的配置信息"}

		# 检查用户权限
		# 1. 检查用户是否是被指派的用户
		# if step.assigned_to and step.assigned_to != user:
		#     # 也可以检查用户的角色权限
		# user_roles = frappe.get_roles(user)
		# allowed_roles = []  # 可以根据需要定义允许的角色
		# if step.assigned_by_role and step.assigned_by_role not in user_roles:
		#     return {
		#         "valid": False,
		#         "error": f"你没有权限执行此操作。该步骤指派给了 {step.assigned_to}"
		#     }

		# 2. 检查步骤状态
		if step.status == "Completed":
			return {"valid": False, "error": "该步骤已完成，无法再次执行操作"}

		# 3. 检查流程整体状态
		flow = frappe.get_doc("Project", flow_name)
		if flow.status == "Completed":
			return {"valid": False, "error": "整个流程已完成，无法执行操作"}

		# 4. 可以添加更多业务逻辑校验
		# 例如：检查前置步骤是否已完成等

		return {"valid": True, "message": "权限验证通过"}

	except Exception as e:
		frappe.log_error(f"权限验证错误: {str(e)}")
		return {"valid": False, "error": f"权限验证过程中出现错误: {str(e)}"}
	"""
    验证用户是否有权限执行流程操作
    """
	try:
		# 查询对应的Task Flow Step记录
		step = frappe.get_doc("Task Flow Step", {"flow_name": flow_name, "template_step_index": step_index})

		if not step:
			return {"valid": False, "error": f"未找到步骤 {step_index} 的配置信息"}

		# 检查用户权限
		# 1. 检查用户是否是被指派的用户
		# if step.assigned_to and step.assigned_to != user:
		#     # 也可以检查用户的角色权限
		# user_roles = frappe.get_roles(user)
		# allowed_roles = []  # 可以根据需要定义允许的角色
		# if step.assigned_by_role and step.assigned_by_role not in user_roles:
		#     return {
		#         "valid": False,
		#         "error": f"你没有权限执行此操作。该步骤指派给了 {step.assigned_to}"
		#     }

		# 2. 检查步骤状态
		if step.status == "Completed":
			return {"valid": False, "error": "该步骤已完成，无法再次执行操作"}

		# 3. 检查流程整体状态
		flow = frappe.get_doc("Project", flow_name)
		if flow.status == "Completed":
			return {"valid": False, "error": "整个流程已完成，无法执行操作"}

		# 4. 可以添加更多业务逻辑校验
		# 例如：检查前置步骤是否已完成等

		return {"valid": True, "message": "权限验证通过"}

	except Exception as e:
		frappe.log_error(f"权限验证错误: {str(e)}")
		return {"valid": False, "error": f"权限验证过程中出现错误: {str(e)}"}


# 创建Flow Action单据
@frappe.whitelist()
def create_flow_action(flow_name, step_index, action_result, action_sign, step_name, comment=None):
	"""
	创建Flow Action单据
	"""
	# 将参数转换为整数
	step_index = int(step_index)

	# print(f"创建Flow Action单据: {flow_name}, {step_index}, {action_result}, {action_sign}, {comment}")
	try:
		# 再次验证权限（双重保险）
		permission_check = validate_flow_action_permission(flow_name, step_index, frappe.session.user)
		# print(f"权限验证结果: {permission_check}")
		if not permission_check["valid"]:
			return permission_check

		# 创建Flow Action单据
		flow_action = frappe.get_doc(
			{
				"doctype": "Flow Action",
				"custom_project_name": flow_name,
				"flow_step": step_index,
				"action_type": "Approve",  # 可以根据需要调整
				"action_result": action_result,
				"action_sign": action_sign,
				"assigned_role": frappe.session.user,
				"comment": comment or "",
				"step_name": step_name,
			}
		)
		# print("准备插入 Flow Action:", flow_action.as_json())

		flow_action.insert(ignore_permissions=True)

		return {"success": True, "message": "操作记录创建成功", "doc_name": flow_action.name}

	except Exception as e:
		frappe.log_error(f"创建Flow Action失败: {str(e)}")
		return {"success": False, "error": f"创建操作记录失败: {str(e)}"}


# 切换任务流步骤状态（带删除确认）
@frappe.whitelist()
def toggle_task_flow_step_status(
	flow_name,
	template_step_index,
	action,
	confirm_deletion=False,
	is_single_doc_completion=False,
	is_manual_action=False,
	total_idx=0,
):
	"""
	切换任务流步骤状态（带删除确认）
	"""
	try:
		# 将传入的参数转换为整数以确保类型一致
		template_step_index = int(template_step_index)
		total_idx = int(total_idx)

		# 特别处理：如果是撤销完成操作，需要检查当前步骤是否可以被撤销
		if action == "undo":
			# 检查当前步骤之后的所有步骤，如果后面有已完成的步骤，则不能撤销当前步骤
			# 获取所有后续步骤的状态
			for step_index in range(template_step_index + 1, total_idx + 1):
				later_step_status = frappe.get_all(
					"Task Flow Step",
					filters={"flow_name": flow_name, "template_step_index": step_index},
					fields=["status"],
				)

				if later_step_status:
					status = later_step_status[0]["status"]
					# 如果后续步骤中有任何一个已完成，则不能撤销当前步骤
					if status == "Completed":
						return {
							"success": False,
							"message": f"后续步骤 {step_index} 已完成，不能撤销当前步骤的完成状态",
						}
					# 只有当后续步骤是Assigned或其它活动状态（未跳过且未完成）时，才阻止撤销
					# 如果后续步骤是Skipped，则继续检查更后面的步骤
					elif status not in ["Skipped"]:
						# 检查该步骤是否已有单据，如果没有单据则表示尚未真正开始处理
						step_info = frappe.get_all(
							"Task Flow Step",
							filters={"flow_name": flow_name, "template_step_index": step_index},
							fields=["target_doctype", "allow_multiple"],
						)

						if step_info:
							step_info = step_info[0]
							if step_info["target_doctype"]:
								# 如果步骤关联了单据类型，检查是否已创建相关单据
								related_docs = frappe.get_all(
									step_info["target_doctype"],
									filters={"custom_project_name": flow_name, "flow_step": step_index},
									fields=["name"],
								)

								# 如果允许多单据或者已经有单据创建，则认为该步骤正在处理中
								if step_info["allow_multiple"] and len(related_docs) > 0:
									print(step_info)
									return {
										"success": False,
										"message": f"后续步骤 {step_index} 仍需处理，不能撤销当前步骤的完成状态",
									}
								# 否则，即使状态是Assigned，如果没有单据，也可能允许撤销
							else:
								# 如果没有关联单据类型，但仍不是跳过或完成状态，则不允许撤销
								return {
									"success": False,
									"message": f"后续步骤 {step_index} 仍需处理，不能撤销当前步骤的完成状态",
								}
				else:
					# 如果步骤不存在，继续检查下一个
					continue

		# 获取步骤记录
		step_doc = frappe.get_all(
			"Task Flow Step",
			filters={"flow_name": flow_name, "template_step_index": template_step_index},
			fields=["name", "status", "allow_multiple", "target_doctype", "allow_skip"],
			limit=1,
		)

		if not step_doc:
			return {"success": False, "message": "步骤不存在"}

		step_doc = step_doc[0]
		current_status = step_doc.status

		# 检查权限：确保当前用户有权执行此操作
		# 如果步骤有指派用户，检查是否为当前用户
		if step_doc.get("assigned_to") and step_doc["assigned_to"] != frappe.session.user:
			# 如果不是指派用户，检查用户角色是否允许执行此操作
			allowed_roles = ["System Manager", "Administrator"]
			user_roles = frappe.get_roles(frappe.session.user)
			if not any(role in allowed_roles for role in user_roles):
				return {"success": False, "message": "您没有权限执行此操作"}

		if action == "do":
			# 完成步骤
			if current_status == "Completed":
				return {"success": False, "message": "步骤已完成，无需重复操作"}

			# 检查前置步骤是否已完成或被跳过（确保流程顺序）
			if template_step_index > 1:
				prev_step_status = frappe.get_all(
					"Task Flow Step",
					filters={"flow_name": flow_name, "template_step_index": template_step_index - 1},
					fields=["status"],
				)

				if prev_step_status:
					prev_status = prev_step_status[0]["status"]
					# 前置步骤必须是完成状态或跳过状态才能完成当前步骤
					if prev_status not in ["Completed", "Skipped"]:
						return {
							"success": False,
							"message": f"前置步骤 {template_step_index - 1} 尚未完成或跳过，不能完成当前步骤",
						}

			# 使用 doc 对象进行更新
			step = frappe.get_doc("Task Flow Step", step_doc["name"])
			step.status = "Completed"
			step.completed_at = frappe.utils.now_datetime()
			step.save()

			# 清除缓存以确保状态立即更新
			frappe.db.commit()
			frappe.clear_cache(doctype="Task Flow Step")

			action_msg = "已自动完成（单据创建触发）" if is_single_doc_completion else "已完成（手动操作）"
			return {"success": True, "message": f"步骤 {template_step_index} {action_msg}"}

		elif action == "undo":
			if current_status != "Completed":
				return {"success": False, "message": "步骤尚未完成，无需撤销"}

			# 检查是否为单据步骤
			is_single_doc_step = not step_doc.allow_multiple

			if is_single_doc_step and step_doc.target_doctype:
				# 获取该步骤创建的单据
				related_docs = frappe.get_all(
					step_doc.target_doctype,
					filters={"custom_project_name": flow_name, "flow_step": template_step_index},
					fields=["name"],
				)

				if related_docs and not confirm_deletion:
					# 如果有关联单据但未确认删除，返回需要确认的信息
					# 生成单据链接列表
					doc_links = []
					for doc_info in related_docs:
						# 使用正则表达式确保使用连字符而不是下划线
						import re

						doctype_url = re.sub(r"[ _\s]+", "-", step_doc.target_doctype.lower())
						doc_url = f"/app/{doctype_url}/{doc_info.name}"

						doc_links.append(f'<a href="{doc_url}" target="_blank">{doc_info.name}</a>')

					docs_list_html = "<br>" + "<br>".join(doc_links)

					return {
						"success": False,
                        "message": f"{_('This step has {0} associated document(s). These documents must be deleted before undoing the completion. Please confirm the action.',[len(related_docs)])}{docs_list_html}",
						"needs_confirmation": True,
						"related_docs_count": len(related_docs),
						"related_docs": [doc.name for doc in related_docs],
						"related_docs_urls": [f"/app/{doc_url}/{doc.name}" for doc in related_docs],
					}

				# 如果需要删除单据且已确认
				if related_docs and confirm_deletion:
					# 删除关联的单据
					for doc_info in related_docs:
						try:
							frappe.delete_doc(
								step_doc.target_doctype, doc_info.name, force=1, ignore_permissions=True
							)
							# print(f"已删除关联单据: {step_doc.target_doctype}/{doc_info.name}")
						except Exception as delete_error:
							frappe.log_error(
								f"删除关联单据失败: {step_doc.target_doctype}/{doc_info.name}, 错误: {str(delete_error)}"
							)
							return {
								"success": False,
                                "message": f"{_('Failed to delete associated document {0}.',[doc_info.name])}: {str(delete_error)}"
							}

			# 撤销完成状态
			step = frappe.get_doc("Task Flow Step", step_doc["name"])
			step.status = "Assigned"
			step.completed_at = None
			step.save()

			# 检查是否为最后一步，如果是则更新Task Flow的status为Running
			# 获取流程的所有步骤数量
			total_steps = frappe.db.count("Task Flow Step", {"flow_name": flow_name})
			if template_step_index == total_steps:
				# 更新Task Flow的status为Running
				task_flow = frappe.get_doc("Project", flow_name)
				task_flow.status = "Open"
				task_flow.save()
				# print(f"更新Task Flow {flow_name} 的状态为 Running")

			# 清除缓存以确保状态立即更新
			frappe.db.commit()
			frappe.clear_cache(doctype="Task Flow Step")

			# 验证状态是否确实被更新
			updated_step = frappe.get_doc("Task Flow Step", step_doc["name"])
			if updated_step.status != "Assigned":
				frappe.log_error(f"Failed to update status for step {step_doc['name']}. Current status: {updated_step.status}")
				return {"success": False, "message": _("Failed to update step status. Current status: {0}.",[updated_step.status])}

			# message_suffix = f"，已删除 {len(related_docs)} 个关联单据" if (is_single_doc_step and step_doc.target_doctype and related_docs) else ""
			# success_message = f"步骤 {template_step_index} 已撤销完成状态{message_suffix}"

			# frappe.msgprint(success_message, alert=True)
			return {"success": True, "message": f"步骤 {template_step_index} 已撤销完成状态"}

		return {"success": False, "message": "无效的操作类型"}

	except Exception as e:
		frappe.log_error(f"Error toggling step status: {str(e)}")
		# print(f"111错误: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def update_due_status_for_flows():
	# print("update_due_status_for_flows============================")
	today = getdate()
	due_soon_days = 3  # ⭐ 临近逾期阈值（你可以改）

	# 1️⃣ 取所有未完成的 Task Flow
	flows = frappe.get_all("Project", filters={"status": ["!=", "Completed"]}, fields=["name", "status"])

	updated = []

	for flow in flows:
		# 2️⃣ 取该流程下所有步骤
		steps = frappe.get_all(
			"Task Flow Step", filters={"flow_name": flow.name}, fields=["completed_at", "due_date"]
		)

		# 只看未完成步骤
		pending_steps = [st for st in steps if not st.completed_at]

		if not pending_steps:
			continue

		has_overdue = False
		has_due_soon = False

		for st in pending_steps:
			if not st.due_date:
				continue

			due_date = getdate(st.due_date)

			if due_date < today:
				has_overdue = True
				break
			elif today <= due_date <= add_days(today, due_soon_days):
				has_due_soon = True

		new_status = None

		if has_overdue:
			new_status = "Overdue"
		elif has_due_soon:
			new_status = "Due Soon"

		# 3️⃣ 只有确实需要变化才更新
		if new_status and flow.status != new_status:
			frappe.db.set_value("Project", flow.name, "status", new_status)
			updated.append({"flow": flow.name, "status": new_status})

	frappe.db.commit()

	return {"updated_count": len(updated), "updated": updated}


@frappe.whitelist()
def get_available_sub_flow_templates(parent_flow_name):
	"""获取可用的子流程模板"""
	# 获取所有可用的流程模板
	templates = frappe.get_all("Flow Templates", fields=["name", "flow_template as flow_template"])

	return templates


@frappe.whitelist()
def get_existing_sub_flow_template(parent_flow_name, flow_step):
	"""获取当前主流程下已有子流程的模板"""
	try:
		# 查询当前主流程下指定步骤的子流程
		sub_flows = frappe.get_all(
			"Sub Task Flow",
			filters={"custom_project_name": parent_flow_name, "flow_step": flow_step},
			fields=["flow_template"],
			limit=1,
		)

		if sub_flows and sub_flows[0].flow_template:
			return {"template_name": sub_flows[0].flow_template}

		return None
	except Exception as e:
		frappe.log_error(f"Error getting existing sub flow template: {str(e)}")
		return None


@frappe.whitelist()
def has_existing_sub_flow(parent_flow_name, flow_step):
	"""检查当前主流程下是否已有子流程"""
	try:
		# 查询当前主流程下指定步骤的子流程
		sub_flows = frappe.get_all(
			"Sub Task Flow",
			filters={"custom_project_name": parent_flow_name, "flow_step": flow_step},
			limit_page_length=1,
		)

		return {"exists": len(sub_flows) > 0}
	except Exception as e:
		frappe.log_error(f"Error checking existing sub flow: {str(e)}")
		return {"exists": False}


@frappe.whitelist()
def get_step_label(template_name, step_index):
	"""获取 Flow Template Step 的步骤标签"""
	try:
		# 使用 frappe.db.get_value 直接查询 Flow Template Step 子表
		step_label = frappe.db.get_value(
			"Flow Template Step", {"parent": template_name, "idx": int(step_index)}, "label"
		)

		if step_label:
			return {"label": step_label}

		return None
	except Exception as e:
		frappe.log_error(f"Error getting step label: {str(e)}")
		return None


@frappe.whitelist()
def get_parent_flow_step_label(parent_flow_name, flow_step):
	"""获取主流程模板对应步骤的标签"""
	try:
		# 获取主流程的模板
		parent_flow_template = frappe.db.get_value("Project", parent_flow_name, "flow_template")
		if not parent_flow_template:
			frappe.log_error(f"Parent flow {parent_flow_name} has no flow_template")
			return None

		# 获取模板中对应步骤的标签
		step_label = frappe.db.get_value(
			"Flow Template Step", {"parent": parent_flow_template, "idx": int(flow_step)}, "label"
		)

		if step_label:
			return {"label": step_label}

		return None
	except Exception as e:
		frappe.log_error(f"Error getting parent flow step label: {str(e)}")
		return None


@frappe.whitelist()
def create_sub_flow_from_template(
	parent_flow_name, template_name, sub_flow_name, description="", flow_step=None
):
	"""根据模板创建子流程实例"""
	try:
		import random
		import string
		from datetime import datetime

		print(f"Creating sub flow from template: {template_name}")

		# 生成唯一的子流程 ID
		unique_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
		sub_flow_id = f"SUB-{datetime.now().strftime('%Y%m%d')}-{unique_suffix}"

		# 获取模板中的步骤
		template_steps = frappe.get_all(
			"Flow Template Step", filters={"parent": template_name}, fields=["*"], order_by="idx asc"
		)

		# 调试日志：记录关键信息
		frappe.log_error(
			title=f"创建子流程：{template_name}",
			message=f"模板步骤数：{len(template_steps)}\n父流程：{parent_flow_name}\n步骤序号：{flow_step}\n子流程名称：{sub_flow_name}",
		)

		if not template_steps:
			frappe.log_error(title="警告：模板没有步骤", message=f"模板 {template_name} 没有任何步骤")

		# 创建新的子流程
		sub_flow_doc = frappe.get_doc(
			{
				"doctype": "Sub Task Flow",
				"custom_project_name": parent_flow_name,  # 关联到主任务流
				"flow_step": flow_step if flow_step else 1,  # 设置为对应主流程的步骤序号，默认为 1
				"sub_flow_name": sub_flow_name,
				"flow_template": template_name,
				"description": description,
				"sub_flow_id": sub_flow_id,
				"start_date": frappe.utils.today(),
				"status": "Draft",  # 初始状态为草稿
			}
		)

		sub_flow_doc.insert(ignore_permissions=True)

		# 直接创建 Sub Task Flow Step 记录（非子表方式）
		if template_steps:
			for idx, step in enumerate(template_steps):
				step_doc = frappe.get_doc(
					{
						"doctype": "Sub Task Flow Step",
						"flow_name": sub_flow_doc.name,  # 关联到父流程
						"step_index": idx + 1,
						"step_label": step.label,
						"target_doctype": step.target_doctype,
						"assigned_to": step.assigned_role,
						"due_date": frappe.utils.add_days(frappe.utils.today(), step.default_days or 0),
						"allow_multiple": step.allow_multiple,
						"allow_skip": step.allow_skip,
					}
				)
				step_doc.insert(ignore_permissions=True)

			# 设置步骤总数和进度
			sub_flow_doc.total_steps = len(template_steps)
			sub_flow_doc.completed_steps = 0
			sub_flow_doc.progress = 0

			frappe.log_error(
				title=f"子流程保存前：{sub_flow_doc.name}", message=f"创建了 {len(template_steps)} 个步骤"
			)
		else:
			frappe.log_error(
				title=f"警告：{sub_flow_doc.name} 没有步骤数据",
				message=f"模板 {template_name} 没有步骤，跳过步骤创建",
			)

		# 保存子流程
		sub_flow_doc.save(ignore_permissions=True)

		# 调试日志
		print(f"子流程创建成功：{sub_flow_doc.name}")

		return {
			"name": sub_flow_doc.name,
			"message": "Sub flow created successfully",  # 子流程创建成功
		}
	except Exception as e:
		# 详细记录错误
		import traceback

		error_details = traceback.format_exc()
		print(f"创建子流程失败：{error_details}")

		# 只记录错误信息，避免标题过长
		error_msg = str(e)
		# 截取前 100 个字符作为日志标题
		short_error = error_msg[:100] if len(error_msg) > 100 else error_msg
		frappe.log_error(
			title=f"创建子流程失败：{short_error}",
			message=f"Error creating sub flow from template:\n{error_details}",
		)
		return None


# ==================== 子流程相关 API - 新增 ====================


@frappe.whitelist()
def get_sub_flows_for_step(flow_name: str, template_step_index: int):
	"""获取指定步骤的所有子流程"""
	try:
		sub_flows = frappe.get_all(
			"Sub Task Flow",
			filters={"custom_project_name": flow_name, "flow_step": template_step_index},
			fields=[
				"name",
				"flow_template",
				"progress",
				"total_steps",
				"completed_steps",
				"sub_flow_status",
				"description",
				"start_date",
				"due_date",
				"completion_date",
				"assigned_to",
			],
			order_by="creation desc",
		)

		return sub_flows
	except Exception as e:
		frappe.log_error(f"Error getting sub flows for step: {str(e)}")
		return []


@frappe.whitelist()
def create_sub_flow(flow_name: str, template_step_index: int, flow_template: str, description: str = ""):
	"""为指定步骤创建新的子流程"""
	try:
		# 获取主流程文档
		task_flow = frappe.get_doc("Project", flow_name)

		# 获取步骤信息
		step = frappe.get_doc(
			"Task Flow Step", {"flow_name": flow_name, "template_step_index": template_step_index}
		)

		# 创建子流程
		sub_flow = frappe.get_doc(
			{
				"doctype": "Sub Task Flow",
				"custom_project_name": flow_name,
				"flow_step": template_step_index,
				"flow_template": flow_template,
				"description": description,
				"start_date": frappe.utils.today(),
				"sub_flow_status": "Pending",
				"assigned_to": step.assigned_to or "",
			}
		)

		sub_flow.insert(ignore_permissions=True)

		# 从模板创建步骤
		if flow_template:
			create_steps_from_template(sub_flow.name, flow_template)

		return {"success": True, "name": sub_flow.name, "message": "子流程创建成功"}
	except Exception as e:
		frappe.log_error(f"Error creating sub flow: {e!s}")
		return {"success": False, "message": f"创建子流程失败: {e!s}"}


@frappe.whitelist()
def check_and_update_sub_flow_step(flow_name: str, template_step_index: int):
	"""检查子流程完成情况,更新父步骤状态"""
	try:
		# 获取该步骤的所有子流程
		sub_flows = frappe.get_all(
			"Sub Task Flow",
			filters={"custom_project_name": flow_name, "flow_step": template_step_index},
			fields=["sub_flow_status"],
		)

		if not sub_flows:
			return {"success": False, "message": "没有找到子流程"}

		# 检查所有子流程是否都完成
		all_completed = all(sf.sub_flow_status == "Completed" for sf in sub_flows)

		if all_completed:
			# 更新父步骤状态
			step = frappe.get_doc(
				"Task Flow Step", {"flow_name": flow_name, "template_step_index": template_step_index}
			)
			step.status = "Completed"
			step.completed_at = frappe.utils.now_datetime()
			step.save()

			return {"success": True, "message": "所有子流程已完成，父步骤状态已更新"}

		return {"success": False, "message": "子流程尚未全部完成"}
	except Exception as e:
		frappe.log_error(f"Error checking and updating sub flow step: {e!s}")
		return {"success": False, "message": f"检查子流程状态失败: {e!s}"}





@frappe.whitelist()
def get_related_sub_flows(custom_project_name: str, flow_step: int):
	"""获取同一主流程、同一步骤下的所有子流程"""
	try:
		sub_flows = frappe.get_all(
			"Sub Task Flow",
			filters={"custom_project_name": custom_project_name, "flow_step": flow_step},
			fields=[
				"name",
				"flow_template",
				"progress",
				"total_steps",
				"completed_steps",
				"sub_flow_status",
				"description",
				"start_date",
				"due_date",
				"completion_date",
				"assigned_to",
			],
			order_by="creation desc",
		)

		return sub_flows
	except Exception as e:
		frappe.log_error(f"Error getting related sub flows: {e!s}")
		return []




@frappe.whitelist()
def make_purchase_order_from_flow(source_name, target_doc=None, args=None):
    """从 Task Flow 创建采购订单，从项目的 SKU 清单带出物料"""
    if args is None:
        args = {}
    if isinstance(args, str):
        args = json.loads(args)
    if not args and getattr(frappe.flags, 'args', None):
        args = frappe.flags.args

    project_name = args.get("custom_project_name") or source_name
    current_step = int(args.get("flow_step", 0))

    project = frappe.get_doc("Project", project_name)

    po = frappe.new_doc("Purchase Order")
    po.custom_project_name = project_name
    po.flow_step = current_step

    for sku in project.get("custom_sku_list", []):
        if not sku.sku_list_item:
            continue
        po.append("items", {
            "item_code": sku.sku_list_item,
            "qty": sku.item_qty or 1,
            "uom": sku.item_uom or "",
        })

    return po


@frappe.whitelist()
def make_purchase_receipt_from_flow(source_name, target_doc=None, args=None):
    """从 Task Flow 创建采购收货单，自动带出前置步骤 PO 的物料"""
    from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt as erp_make_pr

    if args is None:
        args = {}
    if isinstance(args, str):
        args = json.loads(args)
    if not args and getattr(frappe.flags, 'args', None):
        args = frappe.flags.args

    flow_name = args.get("custom_project_name") or source_name
    current_step = int(args.get("flow_step", 0))

    # 1. 查找当前 flow 中前面的 PO 步骤（已完成的）
    prev_po_steps = frappe.get_all(
        "Task Flow Step",
        filters={
            "flow_name": flow_name,
            "template_step_index": ["<", current_step],
            "target_doctype": "Purchase Order",
            "status": "Completed",
        },
        fields=["template_step_index"],
        order_by="template_step_index desc",
    )

    # 2. 找到已提交的 PO 单据（取最近的步骤）
    po_name = None
    for ps in prev_po_steps:
        po_docs = frappe.get_all(
            "Purchase Order",
            filters={
                "custom_project_name": flow_name,
                "flow_step": ps.template_step_index,
                "docstatus": 1,
            },
            fields=["name"],
            limit=1,
        )
        if po_docs:
            po_name = po_docs[0].name
            break

    def set_missing_values(source, target):
        target.custom_project_name = flow_name
        target.flow_step = current_step

    if po_name:
        # 3. 使用 ERPNext 标准映射 PO → PR
        doc = erp_make_pr(po_name, target_doc)
        # 补上 flow 关联字段（erp_make_pr 不会自动带这些）
        doc.custom_project_name = flow_name
        doc.flow_step = current_step
        return doc

    # 4. 无 PO 则创建空白 PR
    doc = get_mapped_doc(
        "Project",
        flow_name,
        {"Project": {"doctype": "Purchase Receipt", "field_map": {}}},
        target_doc,
        set_missing_values,
    )
    return doc


@frappe.whitelist()
def update_flow_step_on_document_submit(doc, method):
    """doc_events: 单据提交/取消时更新 Task Flow Step 状态"""
    flow_name = doc.get("custom_project_name")
    flow_step = doc.get("flow_step")
    if not flow_name or not flow_step:
        return

    status_map = {0: "Document Created", 1: "Completed", 2: "Ready for Action"}
    new_status = status_map.get(doc.docstatus, "Ready for Action")

    step = frappe.get_all(
        "Task Flow Step",
        filters={"flow_name": flow_name, "template_step_index": flow_step},
        fields=["name"],
        limit=1,
    )

    if step:
        update_data = {
            "status": new_status,
        }
        if new_status == "Completed":
            update_data["completed_at"] = frappe.utils.now_datetime()
        elif new_status == "Ready for Action":
            update_data["completed_at"] = None

        frappe.db.set_value("Task Flow Step", step[0].name, update_data)