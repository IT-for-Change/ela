// Copyright (c) 2025, IT for Change and contributors
// For license information, please see license.txt

function waiting(frm) {
    var wrapper = $(frm.fields_dict['pending_assessment_count_msg'].wrapper);
    wrapper.html("<h4>Waiting...</h4>");
}

frappe.ui.form.on("Activity", {

    refresh(frm) {

        waiting(frm);

        frappe.call({
            method: "ela.ela.doctype.activity.activity.display_assessment_block",
            args: { activity_id: frm.doc.activity_id },
            callback(r) {
                if (r.message > 0) {
                    var wrapper = $(frm.fields_dict['pending_assessment_count_msg'].wrapper);
                    wrapper.html("<h4>" + r.message + " submissions pending assessment</h4>");
                    frm.toggle_display('run_assessment', true);
                }
            }
        });
    },

    run_assessment(frm) {
        frappe.call({
            method: "ela.ela.doctype.activity.activity.run_assessment",
            args: { activity_id: frm.doc.activity_id },
            callback(r) {
                frappe.msgprint(__(r));
            }
        });

    },

    //fn name matches the button name in the activity form page
    create_assessment_form(frm) {
        url = "/app/assessment-form/new?activity=" + frm.doc.name + "&activity_title=" + frm.doc.title;
        window.open(url, "_blank");
    }
});
