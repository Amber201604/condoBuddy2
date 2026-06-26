// console.log("Task Flow..........")
// 在文件开头添加新的操作类型
const FLOW_ACTION_TYPE = {
    ASSIGN: "assign",
    ACTION: "action",
    ALTER: "alter",
    COMPLETE: "complete",
    SKIP: "skip",      // 添加跳过操作类型
    UNSKIP: "unskip"   // 添加取消跳过操作类型
};

const current_user = frappe.session.user_fullname;
let isDataLoaded = false;  // 用于确保数据加载后才渲染
let isRendering = false;   // 确保渲染流程图时不会重复渲染

// 在文件开头添加页面可见性检测
let pageVisibilityState = 'visible';

// 监听页面可见性变化
document.addEventListener('visibilitychange', function() {
    pageVisibilityState = document.visibilityState;
});

// ##################  在列表中检查任务逾期状态  ##################
function set_task_flow_indicator(frm) {
    if (!frm.doc.status) return;

    if (frm.doc.status === 'Overdue') {
        frm.page.set_indicator(__('Overdue'), 'red');
    }
    else if (frm.doc.status === 'Due Soon') {
        frm.page.set_indicator(__('Due soon'), 'orange');
    }else if (frm.doc.status === 'Overdue Completed') {
        frm.page.set_indicator(__('Overdue Completed'), 'green');
    }
    else if (frm.doc.status === 'Completed') {
        frm.page.set_indicator(__('Completed'), 'green');
    }
    else {
        frm.page.set_indicator(__(frm.doc.status), 'grey');
    }
}

// ##################  在单据中执行流程图渲染逻辑  ##################

// 改进清理函数，确保完全清理状态
function clear_flow(frm) {
    const dashboardWrapper = frm.dashboard?.wrapper || document.querySelector(".form-dashboard");
    if (dashboardWrapper) {
        dashboardWrapper.querySelectorAll(".flow-diagram-section").forEach(el => el.remove());
    }

    // 重置所有状态标志
    frm._steps = null;
    frm._loading_steps = false;
    isDataLoaded = false;
    isRendering = false;

    // 清理可能存在的计时器
    if (frm.__refresh_debounce_timer) {
        clearTimeout(frm.__refresh_debounce_timer);
    }
}

// 改进事件绑定函数
function bind_flow_cleanup(frm) {
    if (frm.__flow_cleanup_bound) return;
    frm.__flow_cleanup_bound = true;

    // 绑定路由变化事件
    frm.__on_route_change = () => {
        clear_flow(frm);
    };
    frappe.router.on("change", frm.__on_route_change);

    // 监听页面显示事件，处理后退情况
    frm.__on_pageshow = (event) => {
        if (event.persisted) { // 页面是从缓存恢复的
            setTimeout(() => {
                if (frm.doc && frm.doc.name && frm.doc.doctype === "Task Flow") {
                    force_reload_flow_diagram(frm);
                }
            }, 100);
        } else {
            // 即使不是从缓存恢复，也重新加载流程图
            setTimeout(() => {
                if (frm.doc && frm.doc.name && frm.doc.doctype === "Task Flow") {
                    force_reload_flow_diagram(frm);
                }
            }, 50);
        }
    };
    window.addEventListener("pageshow", frm.__on_pageshow);

    // 页面隐藏时的处理
    frm.__on_pagehide = () => clear_flow(frm);
    window.addEventListener("pagehide", frm.__on_pagehide);
}

// 强制重新加载流程图的函数
function force_reload_flow_diagram(frm) {
    clear_flow(frm);

    // 重新加载步骤数据
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Task Flow Step",
            fields: ["template_step_index", "step_label", "target_doctype", "assigned_to", "due_date","started_at","completed_at","allow_multiple","flow_name", "description"],
            filters: { flow_name: frm.doc.name }
        },
        callback(r) {
            if (r.message) {
                let steps = r.message
                    .sort((a, b) => a.template_step_index - b.template_step_index)
                    .map(st => ({
                        ...st,
                        _docs: [],
                        _assignments: [],
                        _completed: st.status === "Completed",
                        _loading: true
                    }));

                frm._steps = steps;
                load_step_documents_async(frm, steps);
            }
        }
    });
}


frappe.ui.form.on("Task Flow", {

    // setup 钩子会在表单初始化时运行
    setup: function(frm) {
        frm.set_query("flow_template", function() {
            return {
                filters: {
                    "is_active": 1
                }
            };
        });
    },

    on_load: function(frm) {
        // 在每次页面加载时清理状态，确保可以重新渲染
        clear_flow(frm);
    },
    refresh(frm) {
        // 只允许在 Task Flow 页面渲染
        if (frm.doctype !== "Task Flow") return;
        custom_app.utils.add_tour_button(frm, { tour_name: "Task Flow" });

        // 在每次 refresh 时清理状态，确保可以重新渲染
        // 这是关键：不依赖 on_load，而是在 refresh 时主动清理
        if (frm.doc.name && !frm.doc.__islocal) {
            clear_flow(frm);
        }

        // 检查文档是否已保存（有实际的文档名称），新建文档时跳过渲染
        if (!frm.doc.name || frm.doc.__islocal) {
            // 清除之前的 flow 内容（以防从其他文档切换过来时残留）
            const dashboardWrapper = frm.dashboard?.wrapper || document.querySelector(".form-dashboard");
            if (dashboardWrapper) {
                dashboardWrapper.querySelectorAll(".flow-diagram-section").forEach(el => el.remove());
            }
            return;
        }

        // 添加创建子流程的按钮 - 新增功能
        // add_sub_flow_creation_buttons(frm);

        // 设置任务逾期状态
        // set_task_flow_indicator(frm);

        // 清除之前的 flow 内容
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Task Flow Step",
                fields: ["template_step_index", "step_label", "target_doctype", "assigned_to", "due_date","started_at","completed_at","allow_multiple","flow_name","description"], // 移除 task_flow 字段
                filters: { flow_name: frm.doc.name }
            },
            callback(r) {
                if (!r.message) {
                    // 如果没有找到步骤，提前退出
                    return;
                }

                // 准备步骤数据，按 template_step_index 排序
                let steps = r.message
                    .sort((a, b) => a.template_step_index - b.template_step_index)
                    .map(st => ({
                        ...st,
                        _docs: [],
                        _assignments: [],
                        _completed: st.status === "Completed",
                        _loading: true
                    }));

                frm._steps = steps;

                // 触发步骤更新
                load_step_documents_async(frm, steps).then(() => {
                    // 检查是否所有步骤都已完成，只有在全部完成后才更新状态
                    const allNonSkippedStepsCompleted = steps.every(step =>
                        step.status === 'Completed' || step.status === 'Skipped'
                    );

                    if (allNonSkippedStepsCompleted) {
                        // 检查是否有步骤逾期完成
                        const hasOverdue = hasOverdueCompletedSteps(steps);
                        const expectedStatus = hasOverdue ? 'Overdue Completed' : 'Completed';

                        // 只有在所有步骤都完成时才更新文档状态
                        if (frm.doc.status !== 'Completed' && frm.doc.status !== 'Overdue Completed') {
                            frappe.call({
                                method: "frappe.client.set_value",
                                args: {
                                    doctype: frm.doc.doctype,
                                    name: frm.doc.name,
                                    fieldname: "status",
                                    value: expectedStatus
                                },
                                callback: function() {
                                    // 不触发 refresh 事件，直接更新状态字段显示
                                    frm.set_value("status", expectedStatus);
                                    // 只刷新流程图 DOM，不重新渲染
                                    refresh_flow_dom(frm);
                                }
                            });
                        } else if (frm.doc.status !== expectedStatus) {
                            // 如果当前状态与期望状态不同，更新状态
                            frappe.call({
                                method: "frappe.client.set_value",
                                args: {
                                    doctype: frm.doc.doctype,
                                    name: frm.doc.name,
                                    fieldname: "status",
                                    value: expectedStatus
                                },
                                callback: function() {
                                    // 不触发 refresh 事件，直接更新状态字段显示
                                    frm.set_value("status", expectedStatus);
                                    // 只刷新流程图 DOM，不重新渲染
                                    refresh_flow_dom(frm);
                                }
                            });
                        }
                    } else {
                        // 如果不是所有步骤都完成，保持现有状态，不进行修改
                        // 除非当前状态是 Completed 或 Overdue Completed 但实际并未完成所有步骤（这种情况可能需要重新设置为 Running）
                        if (frm.doc.status === 'Completed' || frm.doc.status === 'Overdue Completed') {
                            frappe.call({
                                method: "frappe.client.set_value",
                                args: {
                                    doctype: frm.doc.doctype,
                                    name: frm.doc.name,
                                    fieldname: "status",
                                    value: "Running"
                                },
                                callback: function() {
                                    // 不触发 refresh 事件，直接更新状态字段显示
                                    frm.set_value("status", "Running");
                                    // 只刷新流程图 DOM，不重新渲染
                                    refresh_flow_dom(frm);
                                }
                            });
                        }
                    }

                    // 检查并自动完成单据步骤
                    check_and_complete_single_doc_steps(frm, steps);

                    // 启动时间状态检查器
                    setupTimeStatusChecker(frm);
                });
            }
        });
    }

});

// 渲染流程图骨架
function render_flow_skeleton(frm, steps) {
    // 强化页面类型检查：确保只在 Task Flow 表单页面渲染
    if (isRendering || !steps || steps.length === 0 ||
        !frm.doc || !frm.doc.name || frm.doc.doctype !== "Task Flow") {
        // 如果不在 Task Flow 表单页面，确保清理所有流程图元素
        const dashboardWrapper = frm.dashboard?.wrapper || document.querySelector(".form-dashboard");
        if (dashboardWrapper) {
            dashboardWrapper.querySelectorAll(".flow-diagram-section").forEach(el => el.remove());
        }
        return;
    }

    const dashboardWrapper = frm.dashboard?.wrapper || document.querySelector(".form-dashboard");
    if (!dashboardWrapper) return;

    // 关键修改：在渲染前先清理所有旧的流程图
    dashboardWrapper.querySelectorAll(".flow-diagram-section").forEach(el => el.remove());

    if (frm.doc.status === "Completed") {
        // 已完成状态不再渲染流程图
        return;
    }

    // 设置任务逾期状态
    // set_task_flow_indicator(frm);

    const section = document.createElement("div");
    section.className = "flow-diagram-section";
    section.style.margin = "16px";
    section.innerHTML = render_flow_diagram_horizontal(frm, steps);
    dashboardWrapper.appendChild(section);

    isRendering = true;  // 标记渲染进行中
}


// 渲染流程图
function render_flow_diagram_horizontal(frm, steps) {
    // 按照新规则计算完成步骤数（排除跳过的步骤）
    const completed_steps = steps.reduce((count, st) => {
        // 如果步骤被跳过，则不计入进度计算
        if (st.status === "Skipped") {
            return count;
        }

        // 规则1：允许多建单据的步骤有单据算一步，完成当前步骤算一步
        if (st.allow_multiple) {
            if (st._docs.length > 0) {
                count++; // 有单据算一步
            }
            if (st.status === "Completed") {
                count++; // 完成当前步骤算一步
            }
        }
        // 规则2：不允许多建单据的步骤有单据且完成后算一步
        else {
            if (st._docs.length > 0 && st.status === "Completed") {
                count++; // 有单据且完成后算一步
            }
        }

        return count;
    }, 0);

    // 计算总步数（排除跳过的步骤）
    const non_skipped_steps = steps.filter(st => st.status !== "Skipped");
    const total_possible_points = non_skipped_steps.reduce((total, st) => {
        // 多单据步骤可能有两个点（有单据、完成步骤）
        if (st.allow_multiple) {
            total += 2;
        }
        // 单据步骤可能有一个点（有单据且完成）
        else {
            total++;
        }

        return total;
    }, 0);

    const percent = total_possible_points > 0 ? Math.floor((completed_steps / total_possible_points) * 100) : 0;

	let process_progress_txt = frappe._('Process Progress')
    let progress_html = `
        <div style="margin-bottom:16px;">
            <div style="font-size:13px;margin-bottom:6px;color:#37474f;font-weight:500;">
                ${process_progress_txt}：<b>${percent}%</b>
            </div>
            <div style="width:100%;height:10px;background:#eceff1;border-radius:5px;overflow:hidden;">
                <div style="
                    width:${percent}%;
                    height:100%;
                    background: linear-gradient(90deg, #53d167, #1db12e);
                    transition: width 0.4s ease;
                "></div>
            </div>
        </div>
    `;

    // 修正逻辑：找到第一个未完成且未跳过的步骤，且其所有前置步骤都已完成或跳过
    const findCurrentStep = () => {
        for (let i = 0; i < steps.length; i++) {
            const currentStep = steps[i];

            // 检查当前步骤是否未完成且未跳过
            if ((currentStep.status !== "Completed" && currentStep.status !== "Skipped")) {
                // 检查所有前置步骤是否都已完成或跳过
                const allPreviousCompletedOrSkipped = steps.slice(0, i).every(prevStep =>
                    prevStep.status === "Completed" || prevStep.status === "Skipped"
                );

                if (allPreviousCompletedOrSkipped) {
                    return currentStep.template_step_index;
                }
            }
        }
        return null;
    };

    const current_step_idx = findCurrentStep();

    let html = progress_html;

    html += `<div id="flow-horizontal-container" style="
        display:flex;
        flex-wrap:nowrap;
        overflow-x:auto;
        align-items:flex-start;
        gap:8px;
        position:relative;
        padding-bottom:60px;
    ">`;

    steps.forEach((st, index) => {
        // 获取步骤状态
        const completed = st.status === 'Completed';
        const skipped = st.status === 'Skipped';  // 添加跳过状态检查

        // 检查是否是当前步骤
        const is_current_step = current_step_idx === st.template_step_index;

        // 检查是否被锁定（当前步骤之后的步骤，或者前置步骤未完成）
        const stepIndex = steps.findIndex(s => s.template_step_index === st.template_step_index);
        let is_locked = false;

        if (current_step_idx !== null) {
            // 如果当前步骤存在，那么当前步骤之后的步骤被锁定
            is_locked = st.template_step_index > current_step_idx;

            // 但如果当前步骤之前还有未完成的步骤，也应锁定
            if (!is_locked && stepIndex > 0) {
                const previousSteps = steps.slice(0, stepIndex);
                is_locked = !previousSteps.every(prev =>
                    prev.status === "Completed" || prev.status === "Skipped"
                );
            }
        } else {
            // 如果没有当前步骤，所有步骤都可能是锁定的（取决于它们的前置步骤）
            if (stepIndex > 0) {
                const previousSteps = steps.slice(0, stepIndex);
                is_locked = !previousSteps.every(prev =>
                    prev.status === "Completed" || prev.status === "Skipped"
                );
            }
        }

        // 获取时间状态并应用相应的样式
        const timeStatus = getStepTimeStatus(st.due_date, st.status);
        let highlight_bg, highlight_border, shadow;

        if (skipped) {
            // 跳过状态：灰色系
            highlight_bg = is_current_step ? "#f5f5f5" : "#f5f5f5";
            highlight_border = is_current_step ? "#9e9e9e" : "#bdbdbd";
            shadow = is_current_step ? "0 0 15px rgba(158,158,158,0.6)" : "0 2px 6px rgba(0,0,0,0.08)";
        } else if (timeStatus.status === 'overdue') {
            // 严重逾期：红色系
            highlight_bg = is_current_step ? "#ffebee" : completed ? "#e6fffa" : is_locked ? "#f1f3f5" : "#ffebee";
            highlight_border = is_current_step ? "#d32f2f" : completed ? "#38b2ac" : is_locked ? "#adb5bd" : "#d32f2f";
            shadow = is_current_step ? "0 0 15px rgba(255,152,0,0.6)" : "0 2px 6px rgba(211, 47, 47, 0.2)";
        } else if (timeStatus.status === 'warning') {
            // 警告状态：橙色系
            highlight_bg = is_current_step ? "#fff3e0" : completed ? "#e6fffa" : is_locked ? "#f1f3f5" : "#fff8e1";
            highlight_border = is_current_step ? "#ff9800" : completed ? "#38b2ac" : is_locked ? "#adb5bd" : "#ff9800";
            shadow = is_current_step ? "0 0 15px rgba(255,152,0,0.6)" : "0 2px 6px rgba(255, 152, 0, 0.2)";
        } else {
            // 正常状态：原有样式
            highlight_bg = is_current_step ? "#fff3e0" : completed ? "#e6fffa" : is_locked ? "#f1f3f5" : "#f8f9fa";
            highlight_border = is_current_step ? "#ff9800" : completed ? "#38b2ac" : is_locked ? "#adb5bd" : "#d1d8dd";
            shadow = is_current_step ? "0 0 15px rgba(255,152,0,0.6)" : "0 2px 6px rgba(0,0,0,0.08)";
        }

        const doctype_slug = st.target_doctype ? st.target_doctype.toLowerCase().replace(/ /g, "-") : "";

        // 检查是否是子流程步骤
        const is_sub_flow = st.target_doctype === "Sub Task Flow";

        const assigned_user = st.assigned_to;
        // 是否可以创建单据 条件：指派的用户、是当前步骤、步骤允许多单据或没有单据、步骤未完成且未被跳过
        const can_create = assigned_user === current_user && is_current_step && (!st._docs.length || st.allow_multiple) && !completed && !skipped;  // 新建按钮的显示条件

        const assign_text = assigned_user ? `📌 ${assigned_user}` : `📌 ${frappe._("Assign")}`;

        // 修改指派按钮显示 条件：没有完成的步骤任何用户都可以指派
        const can_assign = !completed && !skipped;


        const list_url = `/app/${doctype_slug}?custom_flow_name=${frm.doc.name}&flow_step=${st.template_step_index}`;
        let view_link;
        if (is_sub_flow) {
            // 子流程的特殊链接逻辑：如果有子流程，跳转到第一个未完成的子流程；如果都完成了，跳转到第一个子流程
            if (st._sub_flows && st._sub_flows.length > 0) {
                const first_uncompleted = st._sub_flows.find(sf => sf.sub_flow_status !== 'Completed');
                view_link = first_uncompleted
                    ? `/app/${doctype_slug}/${first_uncompleted.name}`
                    : `/app/${doctype_slug}/${st._sub_flows[0].name}`;
            } else {
                view_link = list_url;
            }
        } else {
            view_link =
                st._docs.length === 1 || st.allow_multiple === false
                    ? (st._docs[0]?.name ? `/app/${doctype_slug}/${st._docs[0].name}` : list_url)
                    : list_url;
        }

        const actual_finish_date = st.completed_at ? st.completed_at : st.due_date;
        const finish_date_display = actual_finish_date ? frappe.datetime.str_to_user(actual_finish_date) : null;
        const date_label = st.completed_at ? frappe._('Completion Time'): frappe._('Due Date');

        // 子流程步骤：需要所有子流程都已完成才能手动完成步骤
        let all_sub_flows_completed = false;
        if (is_sub_flow && st._sub_flows && st._sub_flows.length > 0) {
            all_sub_flows_completed = st._sub_flows.every(sf => sf.sub_flow_status === 'Completed');
        }

        // 是否可以完成步骤
        const can_complete = st.status !== "Completed" && st.status !== "Skipped" && can_create &&
            (is_sub_flow ? all_sub_flows_completed : st._docs.length > 0 && st.allow_multiple);

        // 是否可以撤销完成步骤 条件：有单据、允许多单据、步骤已完成、指派用户是当前用户
        const can_undo_complete = st.status === "Completed" && assigned_user === current_user;


        // 简化步骤状态显示，添加跳过状态
        let stepStatusText = "";
        if (skipped) {
            stepStatusText = `⏭️${frappe._('Skipped')}`;
        } else if (is_sub_flow) {
            // 子流程步骤的特殊状态显示
            const sub_flows = st._sub_flows || [];
            const total_sub_flows = sub_flows.length;
            if (total_sub_flows > 0) {
                const avg_progress = Math.round(sub_flows.reduce((sum, sf) => sum + (sf.progress || 0), 0) / total_sub_flows);
                const completed_count = sub_flows.filter(sf => sf.sub_flow_status === "Completed").length;
                // stepStatusText = `📊 子流程 ${completed_count}/${total_sub_flows} 完成 (平均进度 ${avg_progress}%)`;
                // stepStatusText = `📊 $${frappe._('Sub-process {0}/{1} completed (average progress {2}%)'.replace('{0}', completed_count))}`;
                stepStatusText = `📊 ${frappe._('Sub-process {0}/{1} completed (average progress {2}%)', [completed_count, total_sub_flows, avg_progress])}`;
            } else {
                stepStatusText = `✖${'No sub-process has been created yet.'}`;
            }
        } else if (st.target_doctype !== "Flow Action") {
            if (st._docs.length > 0) {
                stepStatusText = `✅${frappe._('{0} document(s) created').replace('{0}', st._docs.length)}`;
            } else if (is_locked) {
                stepStatusText = `🔒${frappe._('Waiting for Previous Step')}`;
            } else {
                stepStatusText = `✖${frappe._('No Document Created')}`;
            }
        } else {
            if ((st._docs.length || st._docs.allow_multiple) && st.status === "Completed") {
                stepStatusText = `✅${frappe._('Completed')}`;
            } else if (is_locked) {
                stepStatusText = `🔒${frappe._('Waiting for Previous Step')}`;
            } else {
                stepStatusText = `⏳${frappe._('Waiting for Approval')}`;
            }
        }

        // 添加时间状态信息
        let timeStatusText = "";
        if (!completed && !skipped && st.due_date) {
            if (timeStatus.status === 'overdue') {
                timeStatusText = `🚨 ${frappe._('Overdue by {0} days', [Math.abs(timeStatus.remaining_days)])}`;
            } else if (timeStatus.status === 'warning') {
                timeStatusText = `⚠️ ${frappe._('Expires in {0} days', [timeStatus.remaining_days])}`;
            }
        }

        html += `
        ${st.template_step_index > 1 ? `
<div class="flow-step-card" style="
            display:flex;
    color:${highlight_border};
    flex-direction:column;
    justify-content:space-between;
        align-items: center;
    justify-content: center;
    font-size: 32px;
    flex-shrink:0;
    transition: all 0.3s ease;
    position:relative;


">
❯
</div>` : ""}
<div class="flow-step-card" data-step-idx="${st.template_step_index}" data-current="${is_current_step ? 1 : 0}" data-time-status="${timeStatus.status}" data-status="${st.status}" style="
    display:flex;
    flex-direction:column;
    justify-content:space-between;
    padding:16px;
    border:2px solid ${highlight_border};
    border-radius:10px;
    background:${highlight_bg};
    box-shadow:${shadow};
    min-width:280px;
    flex-shrink:0;
    transition: all 0.3s ease;
    position:relative;
" oncontextmenu="showContextMenu(event, '${frm.doc.name}', ${st.template_step_index}, ${can_complete}, ${can_undo_complete})">

    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
        <div style="font-weight:600;font-size:15px;color:#37474f;">
            ${st.template_step_index}. ${st.step_label}${st.allow_multiple ? `(${frappe._('Multiple documents')})` : ''}
        </div>
        ${timeStatusText ? `<div style="font-size:12px;color:${timeStatus.status === 'overdue' ? '#d32f2f' : '#ff9800'};">${timeStatusText}</div>` : ''}
    </div>

    <div style="font-size:13px;flex-grow:1;color:#607d8b;line-height:1.4;">
        ${st._loading ? "⏳ ${frappe._('Loading...')}" : stepStatusText}
        ${is_sub_flow && st._sub_flows && st._sub_flows.length > 0 ? render_doc_list(st._docs, st) : (st._docs.length ? render_doc_list(st._docs, st) : "")}
    </div>

    <div class="action-buttons" style="font-size:13px;margin-top:10px;color:#0288d1;">
        ${can_create ?
            `<a href="javascript:void(0)" onclick="flow_create_doc('${frm.doc.name}', ${st.template_step_index}, '${st.target_doctype}', this, '${(st.step_label || '').replace(/'/g, "\\'")}', '${(st.description || '').replace(/'/g, "\\'").replace(/\n/g, "\\n")}')">➕ ${frappe._('Create')}</a> | `
            : ''}
        <a href="${view_link}"> 📄 ${frappe._('View')}</a> |
        <a href="javascript:void(0)"
           style="${!can_assign ? 'pointer-events:none;color:#999;' : ''}"
           onclick="${!can_assign ? '' : `flow_assign_popup('${frm.doc.name}',${st.template_step_index},this)`}">
           ${assign_text}
        </a>
    </div>

    <div class="finish-date" style="font-size:13px;margin-top:10px;color:#757575;" id="finish_date_${st.template_step_index}" title="${frappe._('Start Date')}:${st.started_at ? frappe.datetime.str_to_user(st.started_at) : frappe._('Time to be allocated')}, ${st.completed_at ? '${frappe._("Completed at")}:'+frappe.datetime.str_to_user(st.completed_at) : frappe._('Estimated Completion Time')+':'+frappe.datetime.str_to_user(st.due_date)}">
        ${date_label}：${finish_date_display ? finish_date_display : frappe._('Time to be allocated')}
    </div>
                ${can_complete ? `<a
                href="javascript:void(0)"
                style="border-radius: 18px;border: inherit;font-size: 13px;text-align: center;"
                onclick="toggleCompleteStatus('${frm.doc.name}', ${st.template_step_index}, 'do')">
                ${frappe._('Complete Current Step')}</a> ` : ''}
</div>


`;

    });

    html += `</div>`;

    setTimeout(() => {
        const container = document.getElementById("flow-horizontal-container");
        if (!container) return;

        const cards = Array.from(container.getElementsByClassName("flow-step-card"));
        let maxHeight = 0;
        cards.forEach(c => maxHeight = Math.max(maxHeight, c.offsetHeight));
        cards.forEach(c => c.style.height = maxHeight + "px");


        const currentCard = container.querySelector('.flow-step-card[data-current="1"]');
        if (currentCard) currentCard.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });

        isDataLoaded = true;  // 标记数据加载完成
        isRendering = false; // 标记渲染完成
    }, 80);

    // 替换 setTimeout 为更可靠的方法
    queueMicrotask(() => {
        ensure_render_after_dom_ready(frm, steps);
    });
    return html;
}

function ensure_render_after_dom_ready(frm, steps) {
    const checkAndRender = () => {
        const container = document.getElementById("flow-horizontal-container");
        if (container) {
            finalize_rendering(container, frm, steps);
        } else {
            // 如果容器还没准备好，延迟重试
            setTimeout(checkAndRender, 50);
        }
    };

    checkAndRender();
}

function finalize_rendering(container, frm, steps) {
    const cards = Array.from(container.getElementsByClassName("flow-step-card"));
    if (cards.length === 0) {
        // 如果卡片还没渲染好，延迟重试
        setTimeout(() => finalize_rendering(container, frm, steps), 50);
        return;
    }

    let maxHeight = 0;
    cards.forEach(c => maxHeight = Math.max(maxHeight, c.offsetHeight));
    cards.forEach(c => c.style.height = maxHeight + "px");


    const currentCard = container.querySelector('.flow-step-card[data-current="1"]');
    if (currentCard) {
        currentCard.scrollIntoView({
            behavior: "smooth",
            inline: "center",
            block: "nearest"
        });
    }

    isDataLoaded = true;
    isRendering = false;
}
// 改进异步加载函数，添加页面状态检查
function load_step_documents_async(frm, steps) {
    // 检查页面是否仍然在正确的上下文中
    if (!frm.doc || !frm.doc.name || frm.doc.doctype !== "Task Flow") {
        return Promise.resolve();
    }

    if (!steps || steps.length === 0) {
        return Promise.resolve();
    }

    // 使用更可靠的异步处理
    return new Promise((resolve, reject) => {
        const promises = steps.map(st => load_single_step_with_retry(frm, st));

        Promise.all(promises)
            .then(() => {
                // 检查页面状态是否仍然有效
                if (frm.doc && frm.doc.name && frm.doc.doctype === "Task Flow") {
                    // 使用 requestAnimationFrame 确保 DOM 就绪
                    requestAnimationFrame(() => {
                        if (frm.doc && frm.doc.name && frm.doc.doctype === "Task Flow") {
                            render_flow_skeleton(frm, steps);
                        }
                        resolve();
                    });
                } else {
                    resolve();
                }
            })
            .catch(error => {
                console.error('加载步骤文档失败:', error);
                reject(error);
            });
    });
}

// 带重试机制的加载函数
function load_single_step_with_retry(frm, st, maxRetries = 3) {
    let attempts = 0;

    const attemptLoad = () => {
        return load_single_step(frm, st).catch(error => {
            attempts++;
            if (attempts < maxRetries) {
                console.warn(`加载步骤 ${st.template_step_index} 失败，重试第 ${attempts} 次`);
                return new Promise(resolve => setTimeout(resolve, 100 * attempts)).then(attemptLoad);
            }
            throw error;
        });
    };

    return attemptLoad();
}
// 检测浏览器是否支持关键功能
function check_browser_compatibility() {
    const features = {
        promise: typeof Promise !== 'undefined',
        fetch: typeof fetch !== 'undefined',
        dom_parser: typeof DOMParser !== 'undefined',
        set_timeout: typeof setTimeout !== 'undefined'
    };

    const isCompatible = Object.values(features).every(Boolean);

    if (!isCompatible) {
        console.warn('浏览器兼容性问题:', features);
    }

    return isCompatible;
}
// 加载单个步骤的关联单据
function load_single_step(frm, st) {
    return frappe.db.get_list("Task Flow Step", {
        fields: [
            "name",
            "assigned_to",
            "status",
            "started_at",
            "completed_at",
            "due_date",
            "allow_skip"  // 添加 allow_skip 字段
        ],
        filters: {
            flow_name: frm.doc.name,
            template_step_index: st.template_step_index
        },
        limit: 1
    }).then(res => {
        const step = res && res[0];
        // console.log("Loaded Step:", step); // 添加调试日志

        // 指派信息（唯一来源）
        st.assigned_to = step?.assigned_to || null;
        st.status = step?.status;
        st.started_at = step?.started_at;
        st.completed_at = step?.completed_at;
        st.due_date = step?.due_date;
        st.allow_skip = step?.allow_skip;  // 添加 allow_skip 信息

        // 是否完成
        st._completed = st.status === "Completed";

        // 检查是否是子流程步骤
        const is_sub_flow_step = st.target_doctype === "Sub Task Flow";

        if (is_sub_flow_step) {
            // 如果是子流程步骤，加载子流程数据
            return frappe.call({
                method: "custom_app.custom_app.doctype.task_flow.task_flow.get_sub_flows_for_step",
                args: {
                    flow_name: frm.doc.name,
                    template_step_index: st.template_step_index
                }
            }).then(res => {
                st._sub_flows = res.message || [];
                return st._sub_flows;  // 返回子流程数据
            }).catch(err => {
                console.error("加载子流程数据失败:", err);
                st._sub_flows = [];
                return [];
            });
        } else {
            // 如果不是子流程步骤，加载关联单据
            return frappe.db.get_list(st.target_doctype, {
                fields: ["name"],
                filters: {
                    custom_flow_name: frm.doc.name,
                    flow_step: st.template_step_index
                }
            });
        }
    }).then(data => {
        // 处理加载的数据
        if (st.target_doctype === "Sub Task Flow") {
            // 子流程数据已经在 _sub_flows 中
            st._docs = data || [];
        } else {
            // 普通单据数据
            st._docs = data || [];
        }
        st._loading = false;

        // 重要：这里不单独更新状态，而是统一在最后检查所有步骤状态后更新
        // 只有在所有步骤都完成的情况下才更新主文档状态
    });
}

// 检查是否有步骤逾期完成
function hasOverdueCompletedSteps(steps) {
    for (const step of steps) {
        if (step.status === 'Completed' && step.completed_at && step.due_date) {
            // 检查完成时间是否晚于截止时间
            const completionTime = moment(step.completed_at);
            const dueTime = moment(step.due_date);

            if (completionTime.isAfter(dueTime)) {
                return true; // 发现逾期完成的步骤
            }
        }
    }
    return false;
}

// #####################################################################################


// 计算步骤的时间状态
function getStepTimeStatus(due_date, status) {
    if (!due_date || status === 'Completed') {
        return { status: 'normal', remaining_days: null };
    }

    // 获取当前日期和截止日期
    const now = moment();
    const due = moment(due_date);

    // 计算剩余天数（负数表示已逾期）
    const remaining_days = due.diff(now, 'days');

    // 根据剩余天数和配置的阈值确定状态
    const warning_threshold = 2; // 提醒阈值：2天内
    const urgent_threshold = -1; // 紧急阈值：逾期1天

    if (remaining_days <= urgent_threshold) {
        return { status: 'overdue', remaining_days };
    } else if (remaining_days <= warning_threshold) {
        return { status: 'warning', remaining_days };
    } else {
        return { status: 'normal', remaining_days };
    }
}


// 显示右键菜单
window.showContextMenu = function(event, flowName, stepIndex, canComplete, canUndoComplete) {
    event.preventDefault(); // 阻止默认右键菜单
    // 关闭所有已打开的右键菜单
    closeAllContextMenus();

    // 获取当前步骤信息
    const step = cur_frm._steps.find(s => s.template_step_index === stepIndex);
    const isSkipped = step && step.status === 'Skipped';

    // 检查当前步骤之后的步骤是否存在已完成的步骤
    const followingSteps = cur_frm._steps.filter(s => s.template_step_index > stepIndex);
    const hasCompletedFollowingStep = followingSteps.some(followingStep => followingStep.status === 'Completed');

    // 根据是否被跳过以及后续步骤状态决定是否可以取消跳过
    const canUnskip = isSkipped && !hasCompletedFollowingStep;

    // 检查当前步骤是否可以跳过
    const canSkip = step && step.allow_skip && !isSkipped && step.status !== 'Completed';

    // 检查当前步骤是否是子流程类型
    const isSubFlowStep = step && (step.is_sub_flow || step.target_doctype === 'Sub Task Flow');

    // 构建菜单项
    const menuItems = [
        // { text: frappe._('View Details'), action: `showStepDetails('${flowName}', ${stepIndex})`, class: 'disabled' },
        { text: frappe._('Undo Completion Status'), action: `toggleCompleteStatus('${flowName}', ${stepIndex}, 'undo')`, class: canUndoComplete ? '' : 'disabled'},
        { text:  !step.allow_skip ? frappe._('Step skipping is not allowed.') : isSkipped ? frappe._('Cancel skip step') : frappe._('Skip step'), action: isSkipped ? `unskipStep('${flowName}', ${stepIndex})` : `skipStep('${flowName}', ${stepIndex})`, class: (isSkipped && canUnskip) || (!isSkipped && canSkip) ? '' : 'disabled'}
    ];

    // 只有子流程类型的步骤且已有子流程时才添加"创建子流程"选项
    if (isSubFlowStep) {
        // 检查是否已有子流程
        frappe.call({
            method: "custom_app.custom_app.doctype.task_flow.task_flow.has_existing_sub_flow",
            args: {
                parent_flow_name: flowName,
                flow_step: stepIndex
            },
            async: false,  // 同步调用，等待结果
            callback: function(r) {
                if (r.message && r.message.exists) {
                    menuItems.push({ text: frappe._('Create Sub-process'), action: `create_sub_flow_from_step('${flowName}', ${stepIndex})`, class: '' });
                }
            }
        });
    }

    // 创建右键菜单
    const menu = document.createElement('div');
    menu.id = `context-menu-${stepIndex}`;
    menu.className = 'context-menu';
    menu.style.cssText = `
        position: fixed;
        top: ${event.clientY}px;
        left: ${event.clientX}px;
        background: white;
        border: 1px solid #ddd;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        z-index: 10000;
        min-width: 108px;
        font-size: 12px;
    `;

    // 添加菜单项
    menuItems.forEach(item => {
        const menuItem = document.createElement('div');
        menuItem.className = `context-menu-item ${item.class || ''}`;
        menuItem.textContent = item.text;
        menuItem.style.cssText = `
            padding: 8px 12px;
            cursor: pointer;
            border-bottom: 1px solid #eee;
            transition: background-color 0.2s;
        `;

        if (item.class === 'danger') {
            menuItem.style.color = '#e74c3c';
        }
        if (item.class === 'disabled') {
                menuItem.style.pointerEvents = 'none';
                menuItem.style.color = '#999';
        }

        menuItem.onmouseenter = () => {
            menuItem.style.backgroundColor = '#f5f5f5';
        };

        menuItem.onmouseleave = () => {
            menuItem.style.backgroundColor = 'transparent';
        };

        menuItem.onclick = () => {
            if (!item.class.includes('disabled')) {
                eval(item.action); // 执行动作
                closeContextMenu(stepIndex); // 关闭菜单
            }
        };

        menu.appendChild(menuItem);
    });

    // 最后一个项目不需要下边框
    const lastItem = menu.lastChild;
    if (lastItem) {
        lastItem.style.borderBottom = 'none';
    }

    document.body.appendChild(menu);

    // 调整位置以避免超出屏幕边界
    adjustMenuPosition(menu, event);

    // 点击其他地方关闭菜单
    const closeHandler = function(e) {
        if (!menu.contains(e.target)) {
            closeContextMenu(stepIndex);
            document.removeEventListener('click', closeHandler);
        }
    };

    setTimeout(() => {
        document.addEventListener('click', closeHandler);
    }, 10);
};

// 关闭特定的右键菜单
function closeContextMenu(stepIndex) {
    const menu = document.getElementById(`context-menu-${stepIndex}`);
    if (menu) {
        menu.remove();
    }
}

// 关闭所有右键菜单
function closeAllContextMenus() {
    const menus = document.querySelectorAll('.context-menu');
    menus.forEach(menu => menu.remove());
}

// 调整菜单位置避免超出屏幕
function adjustMenuPosition(menu, event) {
    const rect = menu.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    let top = event.clientY;
    let left = event.clientX;

    // 如果菜单超出右侧边界，调整到左侧
    if (left + rect.width > viewportWidth) {
        left = event.clientX - rect.width;
    }

    // 如果菜单超出底部边界，向上调整
    if (top + rect.height > viewportHeight) {
        top = event.clientY - rect.height;
    }

    // 确保菜单不超出左边界
    if (left < 0) {
        left = 0;
    }

    // 确保菜单不超出顶部边界
    if (top < 0) {
        top = 0;
    }

    menu.style.top = `${top}px`;
    menu.style.left = `${left}px`;
}

// 也可以添加键盘快捷键支持（ESC键关闭菜单）
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeAllContextMenus();
    }
});

// 完成或撤销完成步骤
window.toggleCompleteStatus = function(flow_name, step_idx, action) {
    // 首先检查步骤类型
    const step = cur_frm._steps.find(s => s.template_step_index === step_idx);

    // 对于单据步骤，检查是否已经有单据
    if (step && !step.allow_multiple && action === 'do' && step._docs.length === 0) {
        frappe.msgprint(frappe._('The document step requires the document to be created first before it can be completed.'));
        return;
    }

    // 检查后续步骤状态（仅在撤销完成时）
    if (action === 'undo') {
        // 获取当前步骤在数组中的索引
        const currentStepIndex = cur_frm._steps.findIndex(s => s.template_step_index === step_idx);

        // 检查后续所有步骤的状态
        for (let i = currentStepIndex + 1; i < cur_frm._steps.length; i++) {
            const laterStep = cur_frm._steps[i];

            // 如果后续步骤已完成，则不允许撤销当前步骤
            if (laterStep.status === "Completed") {
                frappe.msgprint(frappe._('Subsequent step {0} has already been completed; the completion status of the current step cannot be undone.',[laterStep.template_step_index]));
                return;
            }

            // 如果后续步骤既未跳过也未完成（即仍在等待处理），也不允许撤销当前步骤
            if (laterStep.status !== "Skipped" && laterStep.status !== "Completed") {
                // 检查该步骤是否有单据，如果有则认为正在处理中
                if (laterStep._docs.length > 0) {
                    frappe.msgprint(frappe._('Subsequent step {0} still requires processing; the completion status of the current step cannot be undone.',[laterStep.template_step_index]));
                    return;
                }
            }
        }
    }

    let message = action === 'do' ?
        frappe_("Once completed, documents can no longer be created for this step. Are you sure you want to complete this step?"):
        frappe._("After undoing the completion, you can continue to create documents in this step. Are you sure you want to undo the completion status?");

    frappe.confirm(
        message,
        function() {
            frappe.call({
                method: "custom_app.custom_app.doctype.task_flow.task_flow.toggle_task_flow_step_status",
                args: {
                    flow_name: flow_name,
                    template_step_index: step_idx,
                    action: action,
                    is_manual_action: true,  // 标识这是手动操作
                    total_idx: cur_frm._steps.length  // 传递总步骤数
                },
                callback: function(r) {
                    if (r.message.success) {
                        frappe.show_alert({
                            message: r.message.message,
                            indicator: 'green'
                        });

                        // 更新本地步骤缓存中的状态
                        const step = cur_frm._steps.find(s => s.template_step_index === step_idx);
                        if (step) {
                            if (action === 'undo') {
                                step.status = "Assigned";  // 撤销后状态应该是已指派
                                step.completed_at = null;
                            } else if (action === 'do') {
                                step.status = "Completed";  // 完成后状态是已完成
                                step.completed_at = frappe.datetime.now_datetime();
                            }

                            record_flow_action(cur_frm, step_idx, FLOW_ACTION_TYPE.ALTER, {
                                result: action === 'do' ? frappe._("Complete Step") : frappe._("Undo Completion"),
                                comment: r.message.message,
                                step_type: step.allow_multiple ? 'multiple' : 'single',
                                action_type: 'manual'
                            });
                        }

                        if(step.allow_multiple === false && action !=='do'){
                            // 对于单据步骤，完成后刷新该步骤的单据列表
                            frappe.msgprint(r.message.message);
                        }

                        // 重新加载步骤数据并刷新流程图
                        reload_steps_data_after_completion(cur_frm);
                    } else {
                        frappe.msgprint(r.message.message || frappe._("Operation failed."));
                    }
                },
                error: function(err) {
                    let errorMessage = action === 'do' ? frappe._("An error occurred while completing the step.") : frappe._("An error occurred while undoing the completion.");
                    frappe.msgprint(errorMessage + ": " + err.message);
                }
            });
        },
        function() {
            frappe.show_alert({ message: frappe._("Cancelled."), indicator: "orange" });
        }
    );
}

// 修改 skipStep 函数，在回调中添加状态检查
function skipStep(flowName, stepIndex) {
    frappe.confirm(
        frappe._('Are you sure you want to skip step {0}?',[stepIndex]),
        function() {
            frappe.call({
                method: "custom_app.custom_app.doctype.task_flow.task_flow.skip_task_flow_step",
                args: {
                    flow_name: flowName,
                    template_step_index: stepIndex
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.show_alert({
                            message: r.message.message || frappe._('Step skipped.'),
                            indicator: 'green'
                        });

                        // 记录流程操作
                        record_flow_action(cur_frm, stepIndex, FLOW_ACTION_TYPE.SKIP, {
                            result: frappe._('Skip step'),
                            comment: frappe._("User skipped step {0}",[stepIndex])
                        });

                        // 重新加载步骤数据并刷新界面
                        reload_steps_data_after_completion(cur_frm);
                    }
                },
                error: function(err) {
                    frappe.msgprint( frappe._('An error occurred while skipping the step.') + ": " + err.message);
                }
            });
        },
        function() {
            frappe.show_alert({ message: frappe._('Cancelled.'), indicator: "orange" });
        }
    );
}

// 修改 unskipStep 函数，只检查当前步骤之后的步骤是否已完成
function unskipStep(flowName, stepIndex) {
    // 首先检查当前步骤是否为跳过状态
    const currentStep = cur_frm._steps.find(s => s.template_step_index === stepIndex);
    if (!currentStep) {
        frappe.msgprint(frappe._('Corresponding step not found.'));
        return;
    }

    if (currentStep.status !== 'Skipped') {
        frappe.msgprint('Step {0} is currently in status {1}, not in skip status; cannot cancel skip.',[stepIndex,currentStep.status])
        return;
    }

    // 检查当前步骤之后的步骤是否存在已完成的步骤（只检查已完成，不检查跳过）
    const followingSteps = cur_frm._steps.filter(s => s.template_step_index > stepIndex);
    const hasCompletedFollowingStep = followingSteps.some(step => step.status === 'Completed');

    if (hasCompletedFollowingStep) {
        frappe.msgprint(frappe._('Skipping cannot be cancelled because there are completed steps after step {0}.',[stepIndex]));
        return;
    }

    frappe.confirm(
        `确定要取消跳过步骤 ${stepIndex} 吗？`,
        function() {
            frappe.call({
                method: "custom_app.custom_app.doctype.task_flow.task_flow.unskip_task_flow_step",
                args: {
                    flow_name: flowName,
                    template_step_index: stepIndex
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.show_alert({
                            message: r.message.message || frappe._('Step skip cancelled.'),
                            indicator: 'blue'
                        });

                        // 记录流程操作
                        record_flow_action(cur_frm, stepIndex, FLOW_ACTION_TYPE.UNSKIP, {
                            result: frappe._('Cancel skip step'),
                            comment: frappe._('User cancelled the skip for step {0}.',[stepIndex])
                        });

                        // 重新加载步骤数据并刷新界面
                        reload_steps_data_after_completion(cur_frm);
                    }
                },
                error: function(err) {
                    frappe.msgprint( frappe._('An error occurred while canceling the step skip.') + ": " + err.message);
                }
            });
        },
        function() {
            frappe.show_alert({ message: frappe._('Cancelled.'), indicator: "orange" });
        }
    );
}

// 修改 reload_steps_data_after_completion 函数，确保在取消跳过后重新评估整个流程状态
function reload_steps_data_after_completion(frm) {
    // 防止在已完成状态下无限循环
    if (frm.doc.status === 'Completed' || frm.doc.status === 'Overdue Completed') {
        // 在完成状态下，只更新UI而不触发进一步的自动完成检查
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Task Flow Step",
                fields: ["template_step_index", "step_label", "target_doctype", "assigned_to", "due_date","started_at","completed_at","allow_multiple", "allow_skip", "status"],
                filters: { flow_name: frm.doc.name }
            },
            callback(r) {
                if (r.message) {
                    let steps = r.message
                        .sort((a, b) => a.template_step_index - b.template_step_index)
                        .map(st => ({
                            ...st,
                            _docs: [],
                            _assignments: [],
                            _completed: st.status === "Completed",
                            _loading: true
                        }));

                    frm._steps = steps;
                    load_step_documents_async(frm, steps).then(() => {
                        refresh_flow_dom(frm);
                    });
                }
            }
        });
        return;
    }

    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Task Flow Step",
            fields: ["template_step_index", "step_label", "target_doctype", "assigned_to", "due_date","started_at","completed_at","allow_multiple", "allow_skip", "status"],
            filters: { flow_name: frm.doc.name }
        },
        callback(r) {
            if (r.message) {
                let steps = r.message
                    .sort((a, b) => a.template_step_index - b.template_step_index)
                    .map(st => ({
                        ...st,
                        _docs: [],
                        _assignments: [],
                        _completed: st.status === "Completed",
                        _loading: true
                    }));

                frm._steps = steps;
                load_step_documents_async(frm, steps).then(() => {
                    refresh_flow_dom(frm);

                    // 重新检查并自动完成单据步骤，但前提是流程状态不是Completed
                    if (frm.doc.status !== 'Completed' && frm.doc.status !== 'Overdue Completed') {
                        check_and_complete_single_doc_steps(frm, steps);
                    } else {
                        // 如果流程状态是Completed或Overdue Completed，但步骤状态发生了变化（如取消跳过），可能需要更新状态
                        const allNonSkippedStepsCompleted = steps.every(step =>
                            step.status === 'Completed' || step.status === 'Skipped'
                        );

                        if (!allNonSkippedStepsCompleted) {
                            // 如果不是所有非跳过的步骤都已完成，说明流程状态需要变为Running
                            frappe.call({
                                method: "frappe.client.set_value",
                                args: {
                                    doctype: frm.doc.doctype,
                                    name: frm.doc.name,
                                    fieldname: "status",
                                    value: "Running"
                                },
                                callback: function() {
                                    // console.log('文档状态已更新为 Running');
                                    frm.refresh_field("status");
                                }
                            });
                        } else {
                            // 如果所有步骤都完成，检查是否有逾期情况
                            const hasOverdue = hasOverdueCompletedSteps(steps);
                            const expectedStatus = hasOverdue ? 'Overdue Completed' : 'Completed';

                            if (frm.doc.status !== expectedStatus) {
                                frappe.call({
                                    method: "frappe.client.set_value",
                                    args: {
                                        doctype: frm.doc.doctype,
                                        name: frm.doc.name,
                                        fieldname: "status",
                                        value: expectedStatus
                                    },
                                    callback: function() {
                                        frm.refresh_field("status");
                                    }
                                });
                            }
                        }
                    }
                });
            }
        }
    });
}

// 指派流程步骤弹窗
window.flow_assign_popup = function(flow_name, template_step_index, btn_element, completed) {
    // 如果步骤已经完成，提示用户
    if (completed) {
        frappe.msgprint(frappe._('This step has been completed.'));
        return;
    }

    // 获取当前步骤的指派信息（通过 Task Flow Step 表的 Assigned To 字段）
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Task Flow Step",
            fields: ["assigned_to", "due_date", "name","started_at"],
            filters: { flow_name: flow_name, template_step_index: template_step_index },
            limit: 1
        },
        callback(assign_res) {
            const current_assignment = assign_res.message?.[0] || null;

            // 获取所有启用的用户列表
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "User",
                    fields: ["full_name","name"],
                    filters: { enabled: 1 }
                },
                callback(user_res) {
                    const user_options = user_res.message.map(u => u.full_name).join("\n");

                    // 创建弹窗
                    const d = new frappe.ui.Dialog({
                        title: frappe._('Assign process step'),
                        fields: [
                            {
                                label: frappe._('Assign user'),
                                fieldname: "assigned_user",
                                fieldtype: "Select",
                                options: user_options,
                                default: current_assignment?.assigned_to,
                                reqd: 1
                            },
                            {
                                label: frappe._('Start Date'),
                                fieldname: "started_at",
                                fieldtype: "Date",
                                default: current_assignment?.started_at || frappe.datetime.nowdate(),
                                reqd: 1
                            },
                            {
                                label: frappe._('Expected Completion Date'),
                                fieldname: "finish_date",
                                fieldtype: "Date",
                                default: current_assignment?.due_date || frappe.datetime.add_days(frappe.datetime.nowdate(), 7),
                                reqd: 1
                            }
                        ],
                        primary_action_label: frappe._('Save'),
                        primary_action(values) {
                            // 检查是否有更改
                            if (current_assignment &&
                                values.assigned_user === current_assignment.assigned_to &&
                                values.finish_date === current_assignment.due_date &&
                                values.started_at === current_assignment.started_at) {
                                frappe.msgprint(frappe._('Assignment information has not been changed. Please verify and then save.'));
                                return;
                            }

                            // 日期必须不早于今天
                            const today_str = frappe.datetime.nowdate();
                            if (values.finish_date < today_str) {
                                frappe.msgprint(frappe._('Completion date cannot be earlier than today.'));
                                return;
                            }

                            // 更新指派信息
                            // 先根据 flow_name 和 template_step_index 查找对应的文档名称
                            frappe.call({
                                method: "frappe.client.get_value",
                                args: {
                                    doctype: "Task Flow Step",
                                    filters: {
                                        flow_name: flow_name,
                                        template_step_index: template_step_index
                                    },
                                    fieldname: "name"
                                },
                                callback: function(res) {
                                    if (res.message && res.message.name) {
                                        const doc_name = res.message.name;

                                        // 使用获取到的文档名称进行更新
                                        frappe.call({
                                            method: "frappe.client.set_value",
                                            args: {
                                                doctype: "Task Flow Step",
                                                name: doc_name,
                                                fieldname: {
                                                    assigned_to: values.assigned_user,
                                                    due_date: values.finish_date,
                                                    started_at: values.started_at,
                                                    status: "Assigned" // 标记为已指派
                                                }
                                            },
                                            callback: function(update_res) {
                                                if (update_res.message) {
                                                    d.hide();
                                                    frappe.show_alert({ message: frappe._('Assigned successfully.'), indicator: "green" });

                                                    // 更新界面上的指派信息
                                                    const st = cur_frm._steps.find(s => s.template_step_index === template_step_index);
                                                    if (st) st._assignments = [{ assigned_user: values.assigned_user, finish_date: values.finish_date }];

                                                    // 更新完成日期
                                                    const finish_elem = document.getElementById(`finish_date_${template_step_index}`);
                                                    if (finish_elem) finish_elem.innerText = frappe._('Finish Date') +"：" + frappe.datetime.str_to_user(values.finish_date);

                                                    // 更新指派按钮文本
                                                    if (btn_element) btn_element.innerText = "📌 " + values.assigned_user;

                                                    // 记录流程操作
                                                    record_flow_action(cur_frm, template_step_index, FLOW_ACTION_TYPE.ASSIGN, {
                                                        assigned_user: values.assigned_user,
                                                        finish_date: values.finish_date
                                                    });

                                                    // 重新加载步骤数据并刷新界面
                                                    reload_steps_data_after_completion(cur_frm);
                                                }
                                            }
                                        });
                                    } else {
                                        frappe.msgprint(frappe._('No matching process step record found.'));
                                    }
                                }
                            });
                        }
                    });
                    d.show();
                }
            });
        }
    });
};


// 获取 Flow SKU List 中的商品列表（用于创建 PO 等）
function get_items_from_flow_sku_list() {
    if (!cur_frm.doc.custom_sku_list || !Array.isArray(cur_frm.doc.custom_sku_list) || cur_frm.doc.custom_sku_list.length === 0) {
        return [];
    }

    return cur_frm.doc.custom_sku_list.map(row => ({
        item_code: row.sku_list_item,              // 假设字段名是 sku，指向 Item
        qty: flt(row.item_qty) || 1,          // 数量，转为浮点数
        uom: row.item_uom || "",              // 单位，如果为空系统会自动取默认
    }));
}

// 创建文档
window.flow_create_doc = function(flow, step_idx, target_doctype, btn_element, step_label, description) {
    const doctype_slug = target_doctype.toLowerCase().replace(/ /g, "-");

    // 调试日志

    // 记录流程操作 - 先记录操作
    record_flow_action(cur_frm, step_idx, FLOW_ACTION_TYPE.ACTION, {
        result: frappe._('Create Document'),
        comment: `${frappe._('User clicked "New".')}:${target_doctype}`,
        target_doctype: target_doctype
    });

    if (target_doctype === "Purchase Order" || target_doctype === "Stock Entry") {
        const items = get_items_from_flow_sku_list();
        if (items.length === 0) {
            frappe.msgprint(frappe._('No items available in the associated SKU / associated product. Unable to create a purchase order.'));
            return;
        }

        frappe.model.open_mapped_doc({
			method: "custom_app.custom_app.doctype.task_flow.task_flow.make_purchase_order_from_flow",
			frm: cur_frm,
            args: {
                custom_flow_name: flow,
                flow_step: step_idx,
            },
		});
        return;
    }

    // 构建 URL 参数
    let url_params = `custom_flow_name=${encodeURIComponent(flow)}&flow_step=${step_idx}`;

    // 如果是 Flow Action，添加 step_name 和 specifications 参数（与字段名一致）
    if (target_doctype === "Flow Action") {
        url_params += `&step_name=${encodeURIComponent(step_label || '')}&specifications=${encodeURIComponent(description || '')}`;
    }

    const new_url = `/app/${doctype_slug}/new?${url_params}`;

    // 打开新建单据页面
    window.open(new_url, "_blank");

    // 更新进度条和箭头状态
    update_progress_and_arrows(cur_frm);
};

/** 渲染文档列表 */
function render_doc_list(docs, step_info) {
    // 如果是子流程步骤,显示子流程的进度条和状态
    if (step_info && step_info._sub_flows && step_info._sub_flows.length > 0) {
        let html = `<ul style="margin:6px 0 0 0;font-size:11px;list-style:none;padding-left:0;">`;
        step_info._sub_flows.slice(0, 3).forEach((sf, idx) => {
            const progress = sf.progress || 0;
            const sub_flow_status = sf.sub_flow_status || 'Pending';
            const statusColor = sub_flow_status === 'Completed' ? '#4CAF50' : (sub_flow_status === 'In Progress' ? '#2196F3' : '#9e9e9e');
            html += `<li style="
                padding:4px 6px;
                margin-bottom:4px;
                border-radius:4px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            ">
                <div style="display:flex;justify-content:space-between;margin-bottom:2px;">
                    <span style="font-weight:500;">${sf.name}</span>
                    <span style="color:${statusColor};">${sub_flow_status}</span>
                </div>
                <div style="width:100%;height:4px;background:#e0e0e0;border-radius:2px;overflow:hidden;">
                    <div style="width:${progress}%;height:100%;background:linear-gradient(90deg, #53d167, #1db12e);"></div>
                </div>
            </li>`;
        });
        html += `</ul>`;
        return html;
    }

    // 普通单据列表
    let html = `<ul style="margin:6px 0 0 0;font-size:11px;list-style:none;padding-left:0;">`;
    docs.slice(0, 3).forEach(d => {
        html += `<li style="
            padding:2px 6px;
            margin-bottom:2px;
            border-radius:4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        "> - ${d.name}</li>`;
    });
    html += `</ul>`;
    return html;
}

/** 记录流程操作到活动区 */
function record_flow_action(frm, step_idx, action_type, payload = {}) {
    if (!frm || !frm._steps) return;

    // 如果是特殊索引 -1（表示整个流程完成），创建虚拟步骤对象
    let step;
    if (step_idx === -1) {
        step = {
            template_step_index: -1,
            step_label: frappe._("Entire Process"),
            allow_multiple: false
        };
    } else {
        step = frm._steps.find(s => s.template_step_index === step_idx);
        if (!step) return;
    }

    const content = build_flow_comment({
        type: action_type,
        user: frappe.session.user_fullname,
        step: step,
        payload: payload
    });

    frappe.call({
        method: "frappe.client.insert",
        args: {
            doc: {
                doctype: "Comment",
                comment_type: "Info", // Comment 可以使用 "Workflow" 或 "Info" 作为替代
                reference_doctype: "Task Flow",
                reference_name: frm.doc.name,
                content
            }
        },
        callback() {
            // ❌ 不再更新隐藏字段，不触发刷新
            // 仅刷新流程图
            // load_step_documents(frm, frm._steps);
            frm.refresh_field("comments");
        }
    });

}


/** 根据操作类型生成活动区文案 */
function build_flow_comment({ type, user, step, payload }) {
    // 检查是否是整个流程完成
    if (type === FLOW_ACTION_TYPE.COMPLETE && step && step.template_step_index === -1) {
        // 特殊处理：整个流程完成的情况
        return `
            🎉<span style="color: #13b515ff;font-size: 16px">${payload.result}</span><br>
            ${payload.comment ? `<b>说明：</b>${payload.comment}` : ""}
        `;
    }

    const step_title = `${step.template_step_index}. ${step.step_label}`;
    const operator = `<b>${user}</b>`;
    switch (type) {
        case FLOW_ACTION_TYPE.ASSIGN:
            return `
                📌${frappe._('Assigned at step {0}: {1}.',[step.template_step_index, step.step_label])}
                <br>
                ${frappe._("Assigned to")}：<b>${payload.assigned_user}</b>
                <br>
                ${frappe._("Finish Date")}：<b>${payload.finish_date}</b>
            `;
        case FLOW_ACTION_TYPE.ACTION:
            return `
                ✔${frappe._('Process action executed at step {0}: {1}.',[step.template_step_index, step.step_label])}
                <br>
                ${frappe._("Action Result")}：<b>${payload.result}</b>
                ${payload.comment ? `<br>${frappe._("Comment")}：${payload.comment}` : ""}
            `;
        case FLOW_ACTION_TYPE.ALTER:
            return `
                ✔${frappe._('Process information modified at step {0}: {1}.',[step.template_step_index, step.step_label])}
                <br>
                ${frappe._("Modification result.")}：<b>${payload.result}</b>
                ${payload.comment ? `<br>${frappe._("Comment")}：${payload.comment}` : ""}
            `;
        case FLOW_ACTION_TYPE.SKIP:
            return `
                ⏭️${frappe._('Skipped process at step {0}: {1}.',[step.template_step_index, step.step_label])}
                <br>
                ${payload.comment ? `<b>${frappe._("Reason")}：</b>${payload.comment}` : ""}
            `;
        case FLOW_ACTION_TYPE.UNSKIP:
            return `
                🔁${frappe._('Cancelled skip at step {0}: {1}.',[step.template_step_index, step.step_label])}
                <br>
                ${payload.comment ? `<b>${frappe._("Reason")}：</b>${payload.comment}` : ""}
            `;
        case FLOW_ACTION_TYPE.COMPLETE:
            return `
                ${frappe._('Completed process step at step {0}: {1}.',[step.template_step_index, step.step_label])}
                <br>
            `;
        default:
            return `
                ${frappe._('Performed action on process step at step {0}: {1}.',[step.template_step_index, step.step_label])}
                <br>
            `;
    }
}
/** 结束所有流程 */
function update_progress_and_arrows(frm) {
    const wrapper = document.querySelector(".flow-diagram-section");
    if (!wrapper) return;

    // 重新计算进度，刷新箭头和 UI
    refresh_flow_dom(frm);
}



// 修改检测并自动完成单据步骤函数，将跳过的步骤视为已完成
function check_and_complete_single_doc_steps(frm, steps) {
    // 检查当前流程状态，如果是 Cancelled 或 Completed 或 Overdue Completed，则不再继续检查
    if (frm.doc.status === 'Cancelled' || frm.doc.status === 'Completed' || frm.doc.status === 'Overdue Completed') {
        return;
    }

    // 检查是否所有非跳过的步骤都已完成
    const allNonSkippedStepsCompleted = steps.every(step =>
        step.status === 'Completed' || step.status === 'Skipped'
    );

    if (allNonSkippedStepsCompleted) {
        // 如果所有非跳过的步骤都已完成，记录流程完成状态并更新文档状态
        const flowCompletionPayload = {
            result: frappe._("Process completed."),
            comment: frappe._("All non-skipped steps have been completed."),
            action_type: 'system_auto_record'
        };

        // 使用一个特殊步骤索引来表示整个流程完成
        const flowCompletionStepIndex = -1; // 使用-1表示整个流程完成

        record_flow_action(frm, flowCompletionStepIndex, FLOW_ACTION_TYPE.COMPLETE, flowCompletionPayload);

        // 检查是否有步骤逾期完成
        const hasOverdue = hasOverdueCompletedSteps(steps);
        const newStatus = hasOverdue ? 'Overdue Completed' : 'Completed';

        // 更新当前文档状态
        frappe.call({
            method: "frappe.client.set_value",
            args: {
                doctype: frm.doc.doctype,
                name: frm.doc.name,
                fieldname: "status",
                value: newStatus
            },
            callback: function(r) {
                // 不触发 refresh 事件，直接更新状态字段显示
                frm.set_value("status", newStatus);
                // 只刷新流程图 DOM，不重新渲染
                refresh_flow_dom(frm);
            }
        });

        return; // 如果所有非跳过的步骤都已完成，直接返回，不再继续处理
    } else {
        // 如果不是所有步骤都完成，确保状态是Running（但不强制更新）
        // 注意：这里不修改状态，让状态保持原有状态
        // 如果需要，可以根据业务逻辑决定是否更新为Running
    }

    steps.forEach(step => {
        // 检查是否为单据步骤且未完成且未被跳过
        // 排除子流程步骤（target_doctype === "Sub Task Flow"），因为子流程步骤需要手动完成
        const is_sub_flow_step = step.target_doctype === "Sub Task Flow";
        if (!is_sub_flow_step && !step.allow_multiple && step.status !== 'Completed' && step.status !== 'Skipped') {
            // 检查是否有单据已创建
            if (step._docs && step._docs.length > 0) {
                // 对于单据步骤，只要有单据创建就应该完成
                frappe.call({
                    method: "custom_app.custom_app.doctype.task_flow.task_flow.toggle_task_flow_step_status",
                    args: {
                        flow_name: frm.doc.name,
                        template_step_index: step.template_step_index,
                        action: 'do',
                        is_single_doc_completion: true,  // 标识这是自动完成单据步骤
                        total_idx: steps.length
                    },
                    callback: function(r) {
                        if (r.message.success) {
                            setTimeout(() => {
                                // 重新加载步骤数据并刷新界面
                                reload_steps_data_after_completion(cur_frm);
                            }, 500);
                        }
                    }
                });
            }
        }
    });
}

// 检查并更新时间状态的函数，只在渲染时调用一次
function setupTimeStatusChecker(frm) {
    // 检查并更新时间状态
    if (frm._steps) {
        const hasTimeChanges = frm._steps.some(st => {
            if (st.status !== 'Completed' && st.due_date) {
                const oldStatus = st._timeStatus || getStepTimeStatus(st.due_date, st.status);
                const newStatus = getStepTimeStatus(st.due_date, st.status);

                if (oldStatus.status !== newStatus.status) {
                    st._timeStatus = newStatus;
                    return true;
                }
            }
            return false;
        });
        checkAndShowTimeStatus(frm);
        // // 如果有任何步骤的时间状态发生变化，重新渲染流程图
        // if (hasTimeChanges) {
        //     console.log("Time status changed");
        //     refresh_flow_dom(frm);

        //     // 显示时间状态通知
        //     showTimeStatusNotifications(frm._steps);
        // }
    }

    // 由于只在渲染时检查一次，不需要定时器和清理函数
}


// 显示时间状态通知
function showTimeStatusNotifications(steps) {
    // console.log(steps)
    // 过滤出未完成且未跳过的步骤进行时间状态检查
    const activeSteps = steps.filter(st =>
        st.status !== 'Completed' &&
        st.status !== 'Skipped' &&
        st.due_date
    );

    const overdueSteps = activeSteps.filter(st =>
        getStepTimeStatus(st.due_date, st.status).status === 'overdue'
    );

    const warningSteps = activeSteps.filter(st => {
        const timeStatus = getStepTimeStatus(st.due_date, st.status);
        return timeStatus.status === 'warning' &&
               timeStatus.remaining_days <= 2; // 1天内到期
    });

    // 创建状态消息
    let messages = [];

    if (overdueSteps.length > 0) {
        const overdueMessage = `⚠️ ${frappe._('{} step(s) are overdue.',[overdueSteps.length])} ：${overdueSteps.map(s => s.step_label).join(', ')}`;
        messages.push(overdueMessage);
    }

    if (warningSteps.length > 0) {
        const warningMessage = `⏰ ${frappe._('{0} step(s) have reached their due date.',[overdueSteps.length])}：${warningSteps.map(s => s.step_label).join(', ')}`;
        messages.push(warningMessage);
    }

    // 如果有状态消息，显示提醒
    if (messages.length > 0) {
        const fullMessage = messages.join('<br>');
        frappe.show_alert({
            message: frappe._('Flow') + "：" +steps[0].flow_name+"<br>" + fullMessage,
            indicator: overdueSteps.length > 0 ? 'red' : 'orange'
        });
    } else {
        // 即使没有问题，也可以选择性地显示一个积极的提醒
        // 如果你想显示所有步骤都在正常状态的消息，可以取消下面的注释

        // const normalSteps = activeSteps.filter(st =>
        //     getStepTimeStatus(st.due_date, st.status).status === 'normal'
        // );

        // if (normalSteps.length > 0) {
        //     frappe.show_alert({
        //         message: `✅ 有 ${normalSteps.length} 个步骤状态正常，无逾期风险`,
        //         indicator: 'green'
        //     });
        // }

    }
}

// 辅助函数：检查并显示时间状态
function checkAndShowTimeStatus(frm) {
    if (frm._steps) {
        const hasTimeChanges = frm._steps.some(st => {
            if (st.status !== 'Completed' && st.due_date) {
                const oldStatus = st._timeStatus || getStepTimeStatus(st.due_date, st.status);
                const newStatus = getStepTimeStatus(st.due_date, st.status);

                if (oldStatus.status !== newStatus.status) {
                    st._timeStatus = newStatus;
                    return true;
                }
            }
            return false;
        });

        // 如果有任何步骤的时间状态发生变化，重新渲染流程图
        if (hasTimeChanges) {
            refresh_flow_dom(frm);
        }

        // 总是显示时间状态通知，无论是否有变化
        showTimeStatusNotifications(frm._steps);
    }
}

// ==================== 子流程创建功能 - 新增部分 ====================



// 创建收货检验子流程
function create_receipt_inspection_sub_flow(frm) {
    // 首先检查是否存在收货检验模板
    frappe.call({
        method: "custom_app.custom_app.doctype.task_flow.task_flow.get_existing_sub_flow_template",
        args: {
            custom_flow_name: frm.doc.name,

        },
        callback: function(r) {
            if (r.message) {
                create_sub_flow_instance(frm, r.message, null);
            } else {
                frappe.msgprint(__("No receipt inspection template found"));
            }
        }
    });
}

// 显示模板选择对话框
function show_template_selection_dialog(frm, templates) {
    let options = [];
    templates.forEach(template => {
        options.push({
            label: template.name,
            value: template.name,
            description: template.description
        });
    });

    let default_name = `${options[0]?.label || __("Sub Flow")} - ${frappe.datetime.now_date()}`;

    let d = new frappe.ui.Dialog({
        title: __("Select Sub Flow Template"), // 选择子流程模板
        fields: [
            {
                label: __("Template"), // 模板
                fieldname: "template",
                fieldtype: "Select",
                options: options.map(opt => opt.label),
                reqd: 1,
                onchange: function() {
                    let selected = templates.find(t => t.name === this.get_value());
                    if (selected) {
                        d.set_value("description", selected.description);
                    }
                }
            },
            {
                label: __("Description"), // 描述
                fieldname: "description",
                fieldtype: "Small Text",
                default: options[0]?.description
            }
        ],
        primary_action_label: __("Create"), // 创建
        primary_action(values) {
            let selected_template = templates.find(t => t.name === values.template);
            create_sub_flow_instance(frm, selected_template.name, null, values.description);
            d.hide();
        }
    });
    d.show();
}

// 创建子流程实例
function create_sub_flow_instance(frm, template_name, sub_flow_name, description = "", flow_step = null) {
    frappe.call({
        method: "custom_app.custom_app.doctype.task_flow.task_flow.create_sub_flow_from_template",
        args: {
            parent_flow_name: frm.doc.name,
            template_name: template_name,
            sub_flow_name: sub_flow_name,
            description: description,
            flow_step: flow_step
        },
        callback: function(r) {
            if (r.message) {
                frappe.show_alert({
                    message: __("Sub flow created successfully: ") + r.message.name, // 子流程创建成功：
                    indicator: 'green'
                });

                // 跳转到新创建的子流程页面
                setTimeout(function() {
                    frappe.set_route("Form", "Sub Task Flow", r.message.name);
                }, 500);
            } else {
                frappe.msgprint(__("Failed to create sub flow")); // 创建子流程失败
            }
        },
        error: function(err) {
            frappe.msgprint(__("Error creating sub flow: ") + err.message); // 创建子流程错误：
        }
    });
}

// 显示模板选择对话框（步骤级别）
function show_template_selection_dialog_for_step(frm, templates, stepIndex) {
    let options = [];
    templates.forEach(template => {
        options.push({
            label: template.name,
            value: template.name,
            description: template.description
        });
    });

    let default_name = `${options[0]?.label || __("Sub Flow")} - ${frappe.datetime.now_date()}`;

    let d = new frappe.ui.Dialog({
        title: __("Select Sub Flow Template"), // 选择子流程模板
        fields: [
            {
                label: __("Template"), // 模板
                fieldname: "template",
                fieldtype: "Select",
                options: options.map(opt => opt.label),
                reqd: 1,
                onchange: function() {
                    let selected = templates.find(t => t.name === this.get_value());
                    if (selected) {
                        d.set_value("description", selected.description);
                    }
                }
            },
            {
                label: __("Description"), // 描述
                fieldname: "description",
                fieldtype: "Small Text",
                default: options[0]?.description
            }
        ],
        primary_action_label: __("Create"), // 创建
        primary_action(values) {
            let selected_template = templates.find(t => t.name === values.template);
            create_sub_flow_instance_from_step(frm, selected_template.name, null, values.description, stepIndex);
            d.hide();
        }
    });
    d.show();
}

// 从步骤创建子流程 - 简化版本，不弹窗
function refresh_flow_dom(frm) {
    let hasTimeChanges = false;

    frm._steps.forEach(function(step) {
        let new_time = step.time;
        let old_time = step.old_time;

        if (new_time !== old_time) {
            hasTimeChanges = true;
            step.old_time = new_time;
        }
    });

    if (hasTimeChanges) {
        refresh_flow_dom(frm);
    }

    // 总是显示时间状态通知，无论是否有变化
    showTimeStatusNotifications(frm._steps);
}

// 从步骤创建子流程 - 简化版本，不弹窗
function create_sub_flow_from_step(flowName, stepIndex) {
    // 先查询当前主流程下是否已有子流程
    frappe.call({
        method: "custom_app.custom_app.doctype.task_flow.task_flow.get_existing_sub_flow_template",
        args: {
            parent_flow_name: flowName,
            flow_step: stepIndex
        },
        callback: function(r) {
            if (r.message && r.message.template_name) {
                // 获取主流程模板对应步骤的标签
                get_parent_flow_step_label_and_create(flowName, r.message.template_name, stepIndex);
            } else {
                frappe.msgprint(frappe._("Please create a sub-process first.")); // 请先创建一个子流程
            }
        }
    });
}

// 获取主流程模板步骤标签并创建子流程
function get_parent_flow_step_label_and_create(flowName, template_name, stepIndex) {
    // 调用后端 API 获取主流程模板的步骤标签
    frappe.call({
        method: "custom_app.custom_app.doctype.task_flow.task_flow.get_parent_flow_step_label",
        args: {
            parent_flow_name: flowName,
            flow_step: stepIndex
        },
        callback: function(r) {
            if (r.message && r.message.label) {
                let step_label = r.message.label;
                create_sub_flow_instance_simple(flowName, template_name, stepIndex, step_label);
            } else {
                frappe.msgprint(frappe._("Unable to retrieve step label."));
            }
        }
    });
}

// 直接创建子流程实例（无需对话框）
function create_sub_flow_instance_simple(flowName, template_name, stepIndex, step_label) {
    // 直接创建子流程，由后端自动生成名称
    frappe.call({
        method: "custom_app.custom_app.doctype.task_flow.task_flow.create_sub_flow_from_template",
        args: {
            parent_flow_name: flowName,
            template_name: template_name,
            sub_flow_name: null,  // 不传名称，由后端自动生成
            description: `${step_label} for step ${stepIndex}`,
            flow_step: stepIndex  // 传递步骤序号
        },
        callback: function(r2) {
            if (r2.message) {
                frappe.show_alert({
                    message: __("Sub flow created successfully: ") + r2.message.name, // 子流程创建成功：
                    indicator: 'green'
                });

                // 跳转到新创建的子流程页面
                setTimeout(function() {
                    frappe.set_route("Form", "Sub Task Flow", r2.message.name);
                }, 500);
            } else {
                frappe.msgprint(__("Failed to create sub flow")); // 创建子流程失败
            }
        },
        error: function(err) {
            frappe.msgprint(__("Error creating sub flow: ") + err.message); // 创建子流程错误：
        }
    });
}


// 从步骤创建子流程实例
function create_sub_flow_instance_from_step(frm, template_name, sub_flow_name, description, stepIndex) {
    frappe.call({
        method: "custom_app.custom_app.doctype.task_flow.task_flow.create_sub_flow_from_template",
        args: {
            parent_flow_name: frm.doc.name,
            template_name: template_name,
            sub_flow_name: sub_flow_name,
            description: description,
            flow_step: stepIndex  // 传递步骤序号
        },
        callback: function(r) {
            if (r.message) {
                frappe.show_alert({
                    message: __("Sub flow created successfully for step") + ` ${stepIndex}`, // 步骤的子流程创建成功
                    indicator: 'green'
                });

                // 刷新当前表单
                frm.reload_doc();
            } else {
                frappe.msgprint(__("Failed to create sub flow")); // 创建子流程失败
            }
        },
        error: function(err) {
            frappe.msgprint(__("Error creating sub flow: ") + err.message); // 创建子流程错误
        }
    });
}

// ==================== 子流程渲染相关函数 ====================

// 渲染子流程进度列表
function render_sub_flow_progress_list(sub_flows) {
    if (!sub_flows || sub_flows.length === 0) return "";

    let html = `<div style="margin-top:8px;padding:8px;background:#f5f5f5;border-radius:6px;">`;
    sub_flows.slice(0, 3).forEach((sf, idx) => {
        const progress = sf.progress || 0;
        const status_color = sf.sub_flow_status === "Completed" ? "#4CAF50" : (sf.sub_flow_status === "In Progress" ? "#2196F3" : "#9e9e9e");
        html += `<div style="margin-bottom:4px;font-size:11px;color:#37474f;">
            <div style="display:flex;justify-content:space-between;margin-bottom:2px;">
                <span>${sf.name}</span>
                <span style="color:${status_color};">${sf.sub_flow_status || "Pending"}</span>
            </div>
            <div style="width:100%;height:4px;background:#e0e0e0;border-radius:2px;overflow:hidden;">
                <div style="width:${progress}%;height:100%;background:linear-gradient(90deg, #53d167, #1db12e);"></div>
            </div>
        </div>`;
    });
    if (sub_flows.length > 3) {
        html += `<div style="font-size:10px;color:#757575;text-align:center;">]${frappe._('There {0} sub-process(es) remaining.',[sub_flows.length - 3])}]</div>`;
    }
    html += `</div>`;
    return html;
}


