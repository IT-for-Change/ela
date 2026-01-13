# your_app/install.py
import frappe
from frappe.utils.password import update_password


def after_install():
    email = "teacher@ela.local"
    full_name = "ELA Teacher"
    roles = ["Teacher"]

    if not frappe.db.exists("User", email):
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": full_name,
            "enabled": 1,
            "send_welcome_email": 0
        }).insert(ignore_permissions=True)

        # Assign roles
        for role in roles:
            user.add_roles(role)

        # Set password securely
        update_password(user.name, "teacher@ela.local",
                        logout_all_sessions=True)

        frappe.db.commit()
