frappe.listview_settings['Task Flow'] = {
    add_fields: ['status', 'name', 'due_date', 'completed_at'],
    get_indicator: function (doc) {
        // 1. Define the color map for your specific states
        const status_map = {
            "Draft": "grey",
            "Running": "orange",
            "Completed": "green",
            "Cancelled": "red",
            "Overdue": "red",
            "Overdue Completed": "yellow",
            "Due Soon": "yellow"
        };

        // 2. Get the color based on the status, default to grey if not found
        let color = status_map[doc.status] || "grey";

        // 3. Return: [Label, Color, Filter Condition]
        return [__(doc.status), color, "status,=," + doc.status];
    },

};