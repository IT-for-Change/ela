// Copyright (c) 2025, IT for Change and contributors
// For license information, please see license.txt

frappe.ui.form.on("Activity", {
	refresh(frm) {

	},

    create_assessment_form(frm) {
        url = "/app/assessment-form/new?activity=" + frm.doc.name + "&activity_title=" + frm.doc.title;
        window.open(url, "_blank");
    }
});
