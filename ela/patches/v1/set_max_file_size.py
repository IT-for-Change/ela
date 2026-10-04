import frappe

# set the max file size to 50 mb.
# Although the nginx env is set to 50mb, it is getting overridden by a frappe internal limit of 25mb.


def execute():
    frappe.db.set_single_value(
        "System Settings",
        "max_file_size",
        50,
    )
