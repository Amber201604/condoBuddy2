// Copyright (c) 2026, XP and contributors
// For license information, please see license.txt

frappe.ui.form.on("Flow Action", {
    refresh(frm) {
        // 强制清空 dashboard，防止 Task Flow 的流程图残留
        try {
            frm.dashboard.clear_headline();
            frm.dashboard.clear_comment();
        } catch (e) {}
    }
});