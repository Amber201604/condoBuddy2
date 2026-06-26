import frappe
import json
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt
from frappe.utils import flt, today, add_days, now_datetime,getdate  # 添加这些导入ft


# print("加载 task_flow.py 模块～～～～～～～～～～～～～～～～～～～～～～～")

class TaskFlow(Document):
    # 删除 Task Flow时，删除 Task Flow Step
    def after_delete(self):
        """
        删除 Task Flow时，删除 Task Flow Step
        """
        print("删除 Task Flow时，删除 Task Flow Step",self.name)
        frappe.db.delete("Task Flow Step", {"flow_name": self.name})

    # 创建 Task Flow时，创建 Task Flow Step
    def after_insert(self):
        """
        用于 doc_events: Task Flow 新建后自动生成 Task Flow Step
        """
        # print(f"after_insert triggered for {self.name}")

        if not self.flow_template:
            # print("没有模板，跳过创建步骤")
            return

        try:
            # 注意 Flow Templates 的 DocType 名称
            template = frappe.get_doc("Flow Templates", self.flow_template)
        except frappe.DoesNotExistError:
            frappe.throw(f"Flow Template '{self.flow_template}' 不存在")

        # 开始日期
        started_at = today()
        for step in template.steps:
            due_date  = add_days(started_at, step.default_days) if step.default_days else started_at
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
                "description": step.description  # 同步 Flow Template Step 的 description 字段
            }

            # 只有当 assigned_to 不为空且是一个有效的用户时才设置
            if hasattr(step, 'assigned_to') and step.assigned_to:
                # 检查是否是完整的用户邮箱（链接字段需要的值）还是全名（显示值）
                if "@" in step.assigned_to or step.assigned_to in ["Administrator", "Guest"]:
                    # 这是正确的用户ID，直接使用
                    step_data["assigned_to"] = step.assigned_to
                else:
                    # 如果是全名，尝试查找对应的用户ID
                    user_id = frappe.db.get_value("User", {"full_name": step.assigned_to}, "name")
                    if user_id:
                        step_data["assigned_to"] = user_id
                    # 如果找不到对应的用户ID，则不设置 assigned_to 字段

            # 只有当 assigned_by_role 存在且有效时才设置
            if hasattr(step, 'assigned_by_role') and step.assigned_by_role:
                step_data["assigned_by_role"] = step.assigned_by_role

            frappe.get_doc(step_data).insert(ignore_permissions=True)

            started_at = due_date  # 下一个步骤的开始日期为当前步骤的完成日期

        # 更新 Task Flow 状态
        self.db_set({
            "current_step": 1,
            "status": "Running",
            "started_by": frappe.session.user,
            "started_at": now_datetime()
        })

        # print(f"生成 {len(template.steps)} 个 Task Flow Step 完成")


# 从 Task Flow 创建采购订单
@frappe.whitelist()
def make_purchase_order_from_flow(source_name, target_doc=None, args=None):
    if args is None:
        args = {}
    if isinstance(args, str):
        args = json.loads(args)

    def set_missing_values(source, target):
        # target.run_method("set_missing_values")
        # target.run_method("calculate_taxes_and_totals")
        target.flow_id = frappe.flags.args.flow_id
        target.flow_step = frappe.flags.args.flow_step

    def update_item(obj, target, source_parent):
        target.stock_qty = flt(obj.item_qty)
        target.item_name = obj.sku_list_item
    def select_item(d):
        filtered_items = args.get("filtered_children", [])
        return d.name in filtered_items if filtered_items else True

    # 假设你的商品子表叫 sku_list，字段分别是 sku, qty, uom
    doclist = get_mapped_doc(
        "Task Flow",
        source_name,
        {
            "Task Flow": {
                "doctype": "Purchase Order",
                "field_map": { # ← 这里写父表字段映射
                    "completed_at" : "schedule_date", # 必选：也就是完成时间
                    "owner" : "custom_负责人1", # 负责人

                    # "required_completion_time" : "supplier", # 供应商
                 },
            },
            "Flow SKU List": {   # ← 这里改成你的子表 Doctype 名
                "doctype": "Purchase Order Item",
                "field_map": {
                    "sku_list_item": "item_code",   # 关联商品 → item_code
                    "item_qty": "qty",
                    "item_uom": "uom",
                },
                "postprocess": update_item,
                "condition": select_item,
            },
        },
        target_doc,
        set_missing_values,
    )

    return doclist

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
    step = frappe.get_all("Task Flow Step",
                          filters={"flow_name": flow_name, "template_step_index": template_step_index},
                          fields=["name", "allow_skip", "status", "target_doctype", "assigned_to"])

    if not step:
        frappe.throw(f"Task Flow Step template_step_index={template_step_index} 不存在")

    step = step[0]

    # 检查是否允许跳过
    if not step.get('allow_skip'):
        frappe.throw(f"步骤 {template_step_index} 不允许跳过")

    if step.get('status') == "Completed":
        frappe.throw("该步骤已完成，无法跳过")

    if step.get('status') == "Skipped":
        frappe.throw("该步骤已被跳过")

    # 检查权限：确保当前用户有权执行此操作
    if step.get('assigned_to') and step['assigned_to'] != frappe.session.user:
        # 如果不是指派用户，检查用户角色是否允许执行此操作
        allowed_roles = ['System Manager', 'Administrator']
        user_roles = frappe.get_roles(frappe.session.user)
        if not any(role in allowed_roles for role in user_roles):
            frappe.throw("您没有权限执行此操作")

    # 检查前置步骤是否已完成或被跳过（确保流程顺序）
    if template_step_index > 1:
        prev_step_status = frappe.get_all(
            "Task Flow Step",
            filters={
                "flow_name": flow_name,
                "template_step_index": template_step_index - 1
            },
            fields=["status"]
        )

        # if prev_step_status:
        #     prev_status = prev_step_status[0]["status"]
        #     # 前置步骤必须是完成状态或跳过状态才能跳过当前步骤
        #     if prev_status not in ['Completed', 'Skipped']:
        #         frappe.throw(f"前置步骤 {template_step_index - 1} 尚未完成或跳过，不能跳过当前步骤")

    # 标记为已跳过
    frappe.db.set_value("Task Flow Step", step['name'], {
        "status": "Skipped",
        "completed_at": frappe.utils.now()  # 设置完成时间为当前时间，以便后续步骤可以继续
    })

    # 强制清除缓存以确保状态立即更新
    frappe.db.commit()
    frappe.clear_cache(doctype="Task Flow Step")

    return {
        "message": "步骤已跳过"
    }

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
    step = frappe.get_all("Task Flow Step",
                          filters={"flow_name": flow_name, "template_step_index": template_step_index},
                          fields=["name", "allow_skip", "status", "assigned_to"])

    if not step:
        frappe.throw(f"Task Flow Step template_step_index={template_step_index} 不存在")

    step = step[0]

    # 检查是否允许跳过/取消跳过（虽然取消跳过不限制此字段，但保持一致性）
    if not step.get('allow_skip'):
        frappe.throw(f"步骤 {template_step_index} 不允许跳过/取消跳过")

    if step.get('status') != "Skipped":
        frappe.throw("该步骤未被跳过，无法取消跳过")

    # 检查权限：确保当前用户有权执行此操作
    if step.get('assigned_to') and step['assigned_to'] != frappe.session.user:
        # 如果不是指派用户，检查用户角色是否允许执行此操作
        allowed_roles = ['System Manager', 'Administrator']
        user_roles = frappe.get_roles(frappe.session.user)
        if not any(role in allowed_roles for role in user_roles):
            frappe.throw("您没有权限执行此操作")

    # 检查当前步骤之后的步骤是否存在已完成的步骤（只检查已完成，不检查跳过）
    next_step_index = template_step_index + 1
    next_step = frappe.get_all("Task Flow Step",
                               filters={"flow_name": flow_name, "template_step_index": next_step_index},
                               fields=["status"])

    if next_step and next_step[0].get('status') == 'Completed':
        frappe.throw(f"不允许取消跳过，因为第 {next_step_index} 步已经完成")

    # 检查当前步骤之后的其他步骤是否已完成（遍历所有后续步骤）
    total_steps = frappe.get_all("Task Flow Step",
                                 filters={"flow_name": flow_name},
                                 fields=["template_step_index"],
                                 order_by="template_step_index desc",
                                 limit=1)

    if total_steps:
        max_step_index = total_steps[0].template_step_index
        for check_index in range(next_step_index + 1, max_step_index + 1):
            check_step = frappe.get_all("Task Flow Step",
                                       filters={"flow_name": flow_name, "template_step_index": check_index},
                                       fields=["status"])
            if check_step and check_step[0].get('status') == 'Completed':
                frappe.throw(f"不允许取消跳过，因为第 {check_index} 步已经完成")

    # 取消跳过状态
    frappe.db.set_value("Task Flow Step", step['name'], {
        "status": "Assigned",  # 恢复为已指派状态
        "completed_at": None   # 清除完成时间
    })

    # 强制清除缓存以确保状态立即更新
    frappe.db.commit()
    frappe.clear_cache(doctype="Task Flow Step")

    return {
        "message": "步骤跳过已取消"
    }

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
        step = frappe.get_doc("Task Flow Step", {
            "flow_name": flow_name,
            "template_step_index": step_index
        })

        if not step:
            return {
                "valid": False,
                "error": f"未找到步骤 {step_index} 的配置信息"
            }

        # 检查用户权限
        # 1. 检查用户是否是被指派的用户
        if step.assigned_to and step.assigned_to != user:
            # 检查用户角色是否允许执行此操作
            allowed_roles = ['System Manager', 'Administrator']
            user_roles = frappe.get_roles(user)
            if not any(role in allowed_roles for role in user_roles):
                return {
                    "valid": False,
                    "error": f"你没有权限执行此操作。该步骤指派给了 {step.assigned_to}"
                }

        # 2. 检查步骤状态
        if step.status == "Completed":
            return {
                "valid": False,
                "error": "该步骤已完成，无法再次执行操作"
            }

        # 3. 检查流程整体状态
        flow = frappe.get_doc("Task Flow", flow_name)
        if flow.status == "Completed":
            return {
                "valid": False,
                "error": "整个流程已完成，无法执行操作"
            }

        # 4. 检查前置步骤是否已完成或被跳过（确保流程顺序）
        if step_index > 1:
            prev_step_status = frappe.get_all(
                "Task Flow Step",
                filters={
                    "flow_name": flow_name,
                    "template_step_index": step_index - 1
                },
                fields=["status"]
            )

            if prev_step_status:
                prev_status = prev_step_status[0]["status"]
                # 前置步骤必须是完成状态或跳过状态才能操作当前步骤
                if prev_status not in ['Completed', 'Skipped']:
                    return {
                        "valid": False,
                        "error": f"前置步骤 {step_index - 1} 尚未完成或跳过，不能操作当前步骤"
                    }

        return {
            "valid": True,
            "message": "权限验证通过"
        }

    except Exception as e:
        frappe.log_error(f"权限验证错误: {str(e)}")
        return {
            "valid": False,
            "error": f"权限验证过程中出现错误: {str(e)}"
        }
    """
    验证用户是否有权限执行流程操作
    """
    # 将参数转换为整数
    step_index = int(step_index)

    try:
        # 查询对应的Task Flow Step记录
        step = frappe.get_doc("Task Flow Step", {
            "flow_name": flow_name,
            "template_step_index": step_index
        })

        if not step:
            return {
                "valid": False,
                "error": f"未找到步骤 {step_index} 的配置信息"
            }

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
            return {
                "valid": False,
                "error": "该步骤已完成，无法再次执行操作"
            }

        # 3. 检查流程整体状态
        flow = frappe.get_doc("Task Flow", flow_name)
        if flow.status == "Completed":
            return {
                "valid": False,
                "error": "整个流程已完成，无法执行操作"
            }

        # 4. 可以添加更多业务逻辑校验
        # 例如：检查前置步骤是否已完成等

        return {
            "valid": True,
            "message": "权限验证通过"
        }

    except Exception as e:
        frappe.log_error(f"权限验证错误: {str(e)}")
        return {
            "valid": False,
            "error": f"权限验证过程中出现错误: {str(e)}"
        }
    """
    验证用户是否有权限执行流程操作
    """
    try:
        # 查询对应的Task Flow Step记录
        step = frappe.get_doc("Task Flow Step", {
            "flow_name": flow_name,
            "template_step_index": step_index
        })

        if not step:
            return {
                "valid": False,
                "error": f"未找到步骤 {step_index} 的配置信息"
            }

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
            return {
                "valid": False,
                "error": "该步骤已完成，无法再次执行操作"
            }

        # 3. 检查流程整体状态
        flow = frappe.get_doc("Task Flow", flow_name)
        if flow.status == "Completed":
            return {
                "valid": False,
                "error": "整个流程已完成，无法执行操作"
            }

        # 4. 可以添加更多业务逻辑校验
        # 例如：检查前置步骤是否已完成等

        return {
            "valid": True,
            "message": "权限验证通过"
        }

    except Exception as e:
        frappe.log_error(f"权限验证错误: {str(e)}")
        return {
            "valid": False,
            "error": f"权限验证过程中出现错误: {str(e)}"
        }

#创建Flow Action单据（此函数已弃用，Flow Action 通过 URL 参数传递数据）
@frappe.whitelist()
def create_flow_action(flow_name, step_index, action_result, action_sign, step_name,comment=None):
    """
    创建Flow Action单据（此函数已弃用）
    """
    pass


# 切换任务流步骤状态（带删除确认）
@frappe.whitelist()
def toggle_task_flow_step_status(flow_name, template_step_index, action, confirm_deletion=False, is_single_doc_completion=False, is_manual_action=False,total_idx=0):
    """
    切换任务流步骤状态（带删除确认）
    """
    try:
        # 将传入的参数转换为整数以确保类型一致
        template_step_index = int(template_step_index)
        total_idx = int(total_idx)

        # 特别处理：如果是撤销完成操作，需要检查当前步骤是否可以被撤销
        if action == 'undo':
            # 检查当前步骤之后的所有步骤，如果后面有已完成的步骤，则不能撤销当前步骤
            # 获取所有后续步骤的状态
            for step_index in range(template_step_index + 1, total_idx + 1):
                later_step_status = frappe.get_all(
                    "Task Flow Step",
                    filters={
                        "flow_name": flow_name,
                        "template_step_index": step_index
                    },
                    fields=["status"]
                )

                if later_step_status:
                    status = later_step_status[0]["status"]
                    # 如果后续步骤中有任何一个已完成，则不能撤销当前步骤
                    if status == 'Completed':
                        return {"success": False, "message": f"后续步骤 {step_index} 已完成，不能撤销当前步骤的完成状态"}
                    # 只有当后续步骤是Assigned或其它活动状态（未跳过且未完成）时，才阻止撤销
                    # 如果后续步骤是Skipped，则继续检查更后面的步骤
                    elif status not in ['Skipped']:
                        # 检查该步骤是否已有单据，如果没有单据则表示尚未真正开始处理
                        step_info = frappe.get_all(
                            "Task Flow Step",
                            filters={
                                "flow_name": flow_name,
                                "template_step_index": step_index
                            },
                            fields=["target_doctype", "allow_multiple"]
                        )

                        if step_info:
                            step_info = step_info[0]
                            if step_info["target_doctype"]:
                                # 如果步骤关联了单据类型，检查是否已创建相关单据
                                related_docs = frappe.get_all(
                                    step_info["target_doctype"],
                                    filters={
                                        "custom_flow_name": flow_name,
                                        "flow_step": step_index
                                    },
                                    fields=["name"]
                                )

                                # 如果允许多单据或者已经有单据创建，则认为该步骤正在处理中
                                if step_info["allow_multiple"] and len(related_docs) > 0:
                                    print(step_info)
                                    return {"success": False, "message": f"后续步骤 {step_index} 仍需处理，不能撤销当前步骤的完成状态"}
                                # 否则，即使状态是Assigned，如果没有单据，也可能允许撤销
                            else:
                                # 如果没有关联单据类型，但仍不是跳过或完成状态，则不允许撤销
                                return {"success": False, "message": f"后续步骤 {step_index} 仍需处理，不能撤销当前步骤的完成状态"}
                else:
                    # 如果步骤不存在，继续检查下一个
                    continue

        # 获取步骤记录
        step_doc = frappe.get_all(
            "Task Flow Step",
            filters={
                "flow_name": flow_name,
                "template_step_index": template_step_index
            },
            fields=["name", "status", "allow_multiple", "target_doctype", "allow_skip"],
            limit=1
        )

        if not step_doc:
            return {"success": False, "message": "步骤不存在"}

        step_doc = step_doc[0]
        current_status = step_doc.status

        # 检查权限：确保当前用户有权执行此操作
        # 如果步骤有指派用户，检查是否为当前用户
        if step_doc.get('assigned_to') and step_doc['assigned_to'] != frappe.session.user:
            # 如果不是指派用户，检查用户角色是否允许执行此操作
            allowed_roles = ['System Manager', 'Administrator']
            user_roles = frappe.get_roles(frappe.session.user)
            if not any(role in allowed_roles for role in user_roles):
                return {"success": False, "message": "您没有权限执行此操作"}

        if action == 'do':
            # 完成步骤
            if current_status == "Completed":
                return {"success": False, "message": "步骤已完成，无需重复操作"}

            # 检查前置步骤是否已完成或被跳过（确保流程顺序）
            if template_step_index > 1:
                prev_step_status = frappe.get_all(
                    "Task Flow Step",
                    filters={
                        "flow_name": flow_name,
                        "template_step_index": template_step_index - 1
                    },
                    fields=["status"]
                )

                if prev_step_status:
                    prev_status = prev_step_status[0]["status"]
                    # 前置步骤必须是完成状态或跳过状态才能完成当前步骤
                    if prev_status not in ['Completed', 'Skipped']:
                        return {"success": False, "message": f"前置步骤 {template_step_index - 1} 尚未完成或跳过，不能完成当前步骤"}

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

        elif action == 'undo':
            if current_status != "Completed":
                return {"success": False, "message": "步骤尚未完成，无需撤销"}

            # 检查是否为单据步骤
            is_single_doc_step = not step_doc.allow_multiple

            if is_single_doc_step and step_doc.target_doctype:
                # 获取该步骤创建的单据
                related_docs = frappe.get_all(
                    step_doc.target_doctype,
                    filters={
                        "custom_flow_name": flow_name,
                        "flow_step": template_step_index
                    },
                    fields=["name"]
                )

                if related_docs and not confirm_deletion:
                    # 如果有关联单据但未确认删除，返回需要确认的信息
                    # 生成单据链接列表
                    doc_links = []
                    for doc_info in related_docs:
                        # 使用正则表达式确保使用连字符而不是下划线
                        import re
                        doctype_url = re.sub(r'[ _\s]+', '-', step_doc.target_doctype.lower())
                        doc_url = f"/app/{doctype_url}/{doc_info.name}"

                        doc_links.append(f'<a href="{doc_url}" target="_blank">{doc_info.name}</a>')

                    docs_list_html = "<br>" + "<br>".join(doc_links)

                    return {
                        "success": False,
                        "message": f"{_('This step has {0} associated document(s). These documents must be deleted before undoing the completion. Please confirm the action.',[len(related_docs)])}{docs_list_html}",
                        "needs_confirmation": True,
                        "related_docs_count": len(related_docs),
                        "related_docs": [doc.name for doc in related_docs],
                        "related_docs_urls": [f"/app/{doc_url}/{doc.name}" for doc in related_docs]
                    }

                # 如果需要删除单据且已确认
                if related_docs and confirm_deletion:
                    # 删除关联的单据
                    for doc_info in related_docs:
                        try:
                            frappe.delete_doc(
                                step_doc.target_doctype,
                                doc_info.name,
                                force=1,
                                ignore_permissions=True
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
                task_flow = frappe.get_doc("Task Flow", flow_name)
                task_flow.status = "Running"
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
            return {
                "success": True,
                "message": f"步骤 {template_step_index} 已撤销完成状态"
            }

        return {"success": False, "message": "无效的操作类型"}

    except Exception as e:
        frappe.log_error(f"Error toggling step status: {str(e)}")
        # print(f"111错误: {str(e)}")
        return {"success": False, "message": str(e)}


# @frappe.whitelist()
# def update_overdue_task_flows():
#     """
#     更新逾期和即将逾期的任务流状态
#     """
#     try:
#         # 获取所有非完成状态的Task Flow
#         flows = frappe.get_all(
#             "Task Flow",
#             filters={
#                 "status": ["not in", ["Completed", "Cancelled"]]
#             },
#             fields=["name"]
#         )

#         for flow in flows:
#             update_single_flow_status(flow.name)

#         return {"success": True, "message": f"Updated status for {len(flows)} flows"}
#     except Exception as e:
#         frappe.log_error(f"Error updating overdue task flows: {str(e)}")
#         return {"success": False, "message": str(e)}

# def update_single_flow_status(flow_name):
#     """
#     更新单个流程的状态
#     """
#     # 获取流程步骤
#     steps = frappe.get_all(
#         "Task Flow Step",
#         filters={
#             "flow_name": flow_name,
#             "status": ["in", ["Assigned", "Running"]]
#         },
#         fields=["due_date", "status"]
#     )

#     if not steps:
#         return

#     # 检查是否有逾期步骤
#     has_overdue_steps = any(
#         step.due_date and moment(step.due_date) < moment()
#         for step in steps if step.due_date
#     )

#     # 检查是否有即将逾期的步骤（2天内）
#     has_due_soon_steps = any(
#         step.due_date and 0 <= (moment(step.due_date) - moment()).days() <= 2
#         for step in steps if step.due_date
#     )

#     # 确定新状态
#     new_status = "Running"
#     if has_overdue_steps:
#         new_status = "Overdue"
#     elif has_due_soon_steps:
#         new_status = "Due Soon"

#     # 更新状态
#     if new_status != "Running":
#         frappe.db.set_value("Task Flow", flow_name, "status", new_status)
#         frappe.db.commit()





@frappe.whitelist()
def update_due_status_for_flows():
    # print("update_due_status_for_flows============================")
    today = getdate()
    due_soon_days = 3   # ⭐ 临近逾期阈值（你可以改）

    # 1️⃣ 取所有未完成的 Task Flow
    flows = frappe.get_all(
        "Task Flow",
        filters={"status": ["!=", "Completed"]},
        fields=["name", "status"]
    )

    updated = []

    for flow in flows:
        # 2️⃣ 取该流程下所有步骤
        steps = frappe.get_all(
            "Task Flow Step",
            filters={"flow_name": flow.name},
            fields=["completed_at", "due_date"]
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
            frappe.db.set_value("Task Flow", flow.name, "status", new_status)
            updated.append({
                "flow": flow.name,
                "status": new_status
            })

    frappe.db.commit()

    return {
        "updated_count": len(updated),
        "updated": updated
    }

# ==================== 子流程创建功能 - 新增部分 ====================

# @frappe.whitelist()
# def get_receipt_inspection_template(parent_flow_name):
#     """获取收货检验模板"""
#     try:
#         # 通过 flow_template 字段精确匹配收货检验模板
#         template = frappe.get_all(
#             "Flow Templates",
#             filters={
#                 "flow_template": ["in", ["收货检验", "Receipt Inspection", "收货验收"]],
#                 "is_active": 1
#             },
#             fields=["name", "flow_template"],
#             limit=1
#         )

#         if template:
#             return template[0].name

#         return None
#     except Exception as e:
#         frappe.log_error(f"Error getting receipt inspection template: {str(e)}")
#         return None

@frappe.whitelist()
def get_available_sub_flow_templates(parent_flow_name):
    """获取可用的子流程模板"""
    # 获取所有可用的流程模板
    templates = frappe.get_all(
        "Flow Templates",
        fields=["name", "flow_template as flow_template"]
    )

    return templates

@frappe.whitelist()
def get_existing_sub_flow_template(parent_flow_name, flow_step):
    """获取当前主流程下已有子流程的模板"""
    try:
        # 查询当前主流程下指定步骤的子流程
        sub_flows = frappe.get_all(
            "Sub Task Flow",
            filters={
                "custom_flow_name": parent_flow_name,
                "flow_step": flow_step
            },
            fields=["flow_template"],
            limit=1
        )

        if sub_flows and sub_flows[0].flow_template:
            return {
                "template_name": sub_flows[0].flow_template
            }

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
            filters={
                "custom_flow_name": parent_flow_name,
                "flow_step": flow_step
            },
            limit_page_length=1
        )

        return {
            "exists": len(sub_flows) > 0
        }
    except Exception as e:
        frappe.log_error(f"Error checking existing sub flow: {str(e)}")
        return {
            "exists": False
        }

@frappe.whitelist()
def get_step_label(template_name, step_index):
    """获取 Flow Template Step 的步骤标签"""
    try:
        # 使用 frappe.db.get_value 直接查询 Flow Template Step 子表
        step_label = frappe.db.get_value(
            "Flow Template Step",
            {"parent": template_name, "idx": int(step_index)},
            "label"
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
        parent_flow_template = frappe.db.get_value("Task Flow", parent_flow_name, "flow_template")
        if not parent_flow_template:
            frappe.log_error(f"Parent flow {parent_flow_name} has no flow_template")
            return None

        # 获取模板中对应步骤的标签
        step_label = frappe.db.get_value(
            "Flow Template Step",
            {"parent": parent_flow_template, "idx": int(flow_step)},
            "label"
        )

        if step_label:
            return {"label": step_label}

        return None
    except Exception as e:
        frappe.log_error(f"Error getting parent flow step label: {str(e)}")
        return None

@frappe.whitelist()
def create_sub_flow_from_template(parent_flow_name, template_name, sub_flow_name, description="", flow_step=None):
    """根据模板创建子流程实例"""
    try:
        import random
        import string
        from datetime import datetime
        print(f"Creating sub flow from template: {template_name}")

        # 生成唯一的子流程 ID
        unique_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        sub_flow_id = f"SUB-{datetime.now().strftime('%Y%m%d')}-{unique_suffix}"

        # 获取模板中的步骤
        template_steps = frappe.get_all(
            "Flow Template Step",
            filters={"parent": template_name},
            fields=["*"],
            order_by="idx asc"
        )

        # 调试日志：记录关键信息
        frappe.log_error(
            title=f"创建子流程：{template_name}",
            message=f"模板步骤数：{len(template_steps)}\n父流程：{parent_flow_name}\n步骤序号：{flow_step}\n子流程名称：{sub_flow_name}"
        )

        if not template_steps:
            frappe.log_error(
                title="警告：模板没有步骤",
                message=f"模板 {template_name} 没有任何步骤"
            )

        # 创建新的子流程
        sub_flow_doc = frappe.get_doc({
            "doctype": "Sub Task Flow",
            "custom_flow_name": parent_flow_name,  # 关联到主任务流
            "flow_step": flow_step if flow_step else 1,  # 设置为对应主流程的步骤序号，默认为 1
            "sub_flow_name": sub_flow_name,
            "flow_template": template_name,
            "description": description,
            "sub_flow_id": sub_flow_id,
            "start_date": frappe.utils.today(),
            "status": "Draft"  # 初始状态为草稿
        })

        sub_flow_doc.insert(ignore_permissions=True)

        # 直接创建 Sub Task Flow Step 记录（非子表方式）
        if template_steps:
            for idx, step in enumerate(template_steps):
                step_doc = frappe.get_doc({
                    "doctype": "Sub Task Flow Step",
                    "flow_name": sub_flow_doc.name,  # 关联到父流程
                    "step_index": idx + 1,
                    "step_label": step.label,
                    "target_doctype": step.target_doctype,
                    "assigned_to": step.assigned_role,
                    "due_date": frappe.utils.add_days(frappe.utils.today(), step.default_days or 0),
                    "allow_multiple": step.allow_multiple,
                    "allow_skip": step.allow_skip
                })
                step_doc.insert(ignore_permissions=True)

            # 设置步骤总数和进度
            sub_flow_doc.total_steps = len(template_steps)
            sub_flow_doc.completed_steps = 0
            sub_flow_doc.progress = 0

            frappe.log_error(
                title=f"子流程保存前：{sub_flow_doc.name}",
                message=f"创建了 {len(template_steps)} 个步骤"
            )
        else:
            frappe.log_error(
                title=f"警告：{sub_flow_doc.name} 没有步骤数据",
                message=f"模板 {template_name} 没有步骤，跳过步骤创建"
            )

        # 保存子流程
        sub_flow_doc.save(ignore_permissions=True)

        # 调试日志
        print(f"子流程创建成功：{sub_flow_doc.name}")

        return {
            "name": sub_flow_doc.name,
            "message": "Sub flow created successfully"  # 子流程创建成功
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
            message=f"Error creating sub flow from template:\n{error_details}"
        )
        return None

# ==================== 子流程相关 API - 新增 ====================

@frappe.whitelist()
def get_sub_flows_for_step(flow_name: str, template_step_index: int):
    """获取指定步骤的所有子流程"""
    try:
        sub_flows = frappe.get_all("Sub Task Flow",
            filters={
                "custom_flow_name": flow_name,
                "flow_step": template_step_index
            },
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
                "assigned_to"
            ],
            order_by="creation desc"
        )

        return sub_flows
    except Exception as e:
        frappe.log_error(f"Error getting sub flows for step: {str(e)}")
        return []

@frappe.whitelist()
def create_sub_flow(flow_name: str, template_step_index: int,
                    flow_template: str, description: str = ""):
    """为指定步骤创建新的子流程"""
    try:
        # 获取主流程文档
        task_flow = frappe.get_doc("Task Flow", flow_name)

        # 获取步骤信息
        step = frappe.get_doc("Task Flow Step", {
            "flow_name": flow_name,
            "template_step_index": template_step_index
        })

        # 创建子流程
        sub_flow = frappe.get_doc({
            "doctype": "Sub Task Flow",
            "custom_flow_name": flow_name,
            "flow_step": template_step_index,
            "flow_template": flow_template,
            "description": description,
            "start_date": frappe.utils.today(),
            "sub_flow_status": "Pending",
            "assigned_to": step.assigned_to or ""
        })

        sub_flow.insert(ignore_permissions=True)

        # 从模板创建步骤
        if flow_template:
            create_steps_from_template(sub_flow.name, flow_template)

        return {
            "success": True,
            "name": sub_flow.name,
            "message": "子流程创建成功"
        }
    except Exception as e:
        frappe.log_error(f"Error creating sub flow: {str(e)}")
        return {
            "success": False,
            "message": f"创建子流程失败: {str(e)}"
        }

@frappe.whitelist()
def check_and_update_sub_flow_step(flow_name: str, template_step_index: int):
    """检查子流程完成情况,更新父步骤状态"""
    try:
        # 获取该步骤的所有子流程
        sub_flows = frappe.get_all("Sub Task Flow",
            filters={
                "custom_flow_name": flow_name,
                "flow_step": template_step_index
            },
            fields=["sub_flow_status"]
        )

        if not sub_flows:
            return {"success": False, "message": "没有找到子流程"}

        # 检查所有子流程是否都完成
        all_completed = all(sf.sub_flow_status == "Completed" for sf in sub_flows)

        if all_completed:
            # 更新父步骤状态
            step = frappe.get_doc("Task Flow Step", {
                "flow_name": flow_name,
                "template_step_index": template_step_index
            })
            step.status = "Completed"
            step.completed_at = frappe.utils.now_datetime()
            step.save()

            return {
                "success": True,
                "message": "所有子流程已完成，父步骤状态已更新"
            }

        return {
            "success": False,
            "message": "子流程尚未全部完成"
        }
    except Exception as e:
        frappe.log_error(f"Error checking and updating sub flow step: {str(e)}")
        return {
            "success": False,
            "message": f"检查子流程状态失败: {str(e)}"
        }

@frappe.whitelist()
def get_related_sub_flows(custom_flow_name: str, flow_step: int):
    """获取同一主流程、同一步骤下的所有子流程"""
    try:
        sub_flows = frappe.get_all("Sub Task Flow",
            filters={
                "custom_flow_name": custom_flow_name,
                "flow_step": flow_step
            },
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
                "assigned_to"
            ],
            order_by="creation desc"
        )

        return sub_flows
    except Exception as e:
        frappe.log_error(f"Error getting related sub flows: {str(e)}")
        return []
