# Copyright (c) 2026, CondoBuddy Team and contributors
# For license information, please see license.txt

# sub_flow_doc_events.py
# 处理子流程相关单据的提交和取消事件

import frappe

def on_submit(doc, method):
    """
    单据提交时更新关联的子流程步骤状态
    """
    # 检查是否有关联的子流程
    sub_flow_name = doc.get('custom_sub_flow_name')
    if not sub_flow_name:
        return
    
    try:
        # 调用子流程的状态更新方法
        frappe.call({
            'method': 'condobuddy2_erp.condobuddy2_erp.doctype.task_flow.task_flow.update_sub_task_flow_progress',
            'args': {
                'sub_task_flow_name': sub_flow_name
            }
        })
        frappe.msgprint(f"Sub flow '{sub_flow_name}' progress updated")
    except Exception as e:
        frappe.log_error(f"Error updating sub flow progress on submit: {str(e)}")

def on_cancel(doc, method):
    """
    单据取消时更新关联的子流程步骤状态
    """
    # 检查是否有关联的子流程
    sub_flow_name = doc.get('custom_sub_flow_name')
    if not sub_flow_name:
        return
    
    try:
        # 调用子流程的状态更新方法
        frappe.call({
            'method': 'condobuddy2_erp.condobuddy2_erp.doctype.task_flow.task_flow.update_sub_task_flow_progress',
            'args': {
                'sub_task_flow_name': sub_flow_name
            }
        })
        frappe.msgprint(f"Sub flow '{sub_flow_name}' progress updated")
    except Exception as e:
        frappe.log_error(f"Error updating sub flow progress on cancel: {str(e)}")
