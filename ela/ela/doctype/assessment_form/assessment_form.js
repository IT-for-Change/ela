// Copyright (c) 2025, ITFC and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Assessment Form", {
// 	refresh(frm) {

// 	},
// });


frappe.ui.form.on('Assessment Form', {

    refresh: function(frm) {
       frm.add_custom_button(__('Generate Form'), function() {
        console.log("Save callback triggered.");
        frm.set_value('save_flag', Date.now());
        frm.save(); //dummy save to trigger the before_save backend code
       }, __("ELA Actions"));
    }
});
 