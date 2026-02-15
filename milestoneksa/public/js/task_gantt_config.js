frappe.views.calendar["Task"] = {
    field_map: {
        start: "exp_start_date",
        end: "exp_end_date",
        id: "name",
        title: "subject",
        allDay: "all_day"
    },
    gantt: true,
    filters: [
        {
            fieldname: "project",
            fieldtype: "Link",
            options: "Project",
            label: __("Project")
        }
    ]
};
