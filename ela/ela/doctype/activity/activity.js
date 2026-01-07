// Copyright (c) 2025, IT for Change and contributors
// For license information, please see license.txt

function waiting(frm) {

    var wrapper = $(frm.fields_dict['pending_assessment_count_msg'].wrapper);
    wrapper.html("<h4>Processing...</h4>");
}

function run_assessment(frm, op) {
    frappe.call({
        method: "ela.ela.doctype.activity.activity.run_assessment",
        args: {
            activity_id: frm.doc.activity_id,
            operation: op
        },
        callback(r) {
            frappe.msgprint(__(r));
        }
    });

}

frappe.ui.form.on("Activity", {

    refresh: function (frm) {

        frm.add_custom_button(__('Refresh Assessment Status'), function () {
            waiting(frm);

            frappe.call({
                method: "ela.ela.doctype.activity.activity.display_assessment_block",
                args: { activity_eid: frm.doc.activity_id },
                callback(r) {
                    var wrapper = $(frm.fields_dict['pending_assessment_count_msg'].wrapper);
                    wrapper.html("<h4>" + r.message['total_pending'] + " submission(s) pending assessment. " + "</h4><br/><p>" +
                        r.message['count_speech_separation'] + " submission(s) pending speech separation. " + "<br/>" +
                        r.message['count_language_check'] + " submission(s) pending language check. " + "<br/>" +
                        r.message['count_transcription'] + " submission(s) pending transcription. " + "<br/>" +
                        r.message['count_text_analysis'] + " submission(s) pending text analysis." + "<br/>" +
                        r.message['count_report'] + " submission(s) pending reporting." + "<br/><br/>" +
                        "See assessment log tab for details.</p>");
                    //unhide the field now.
                    frm.set_df_property('pending_assessment_count_msg', 'hidden', 0);

                    if (r.message['count_speech_separation'] == 0) {
                        frm.toggle_display('run_speech_separation', false);
                    }
                    if (r.message['count_language_check'] == 0) {
                        frm.toggle_display('run_language_check', false);
                    }
                    if (r.message['count_transcription'] == 0) {
                        frm.toggle_display('run_speech_to_text', false);
                    }
                    if (r.message['count_text_analysis'] == 0) {
                        frm.toggle_display('run_text_analysis', false);
                    }
                    if (r.message['count_report'] == 0) {
                        frm.toggle_display('run_reporting', false);
                    }

                }
            });
        });
    },

    run_speech_separation(frm) {
        run_assessment(frm, "sdz")
    },

    run_language_check(frm) {
        run_assessment(frm, "langid")
    },

    run_speech_to_text(frm) {
        run_assessment(frm, "stt")
    },

    run_text_analysis(frm) {
        run_assessment(frm, "nlp")
    },

    run_reporting(frm) {
        run_assessment(frm, "report")
    },

    //fn name matches the button name in the activity form page
    create_assessment_form(frm) {
        url = "/app/assessment-form/new?activity=" + frm.doc.name + "&activity_title=" + frm.doc.title;
        window.open(url, "_blank");
    }
});
