# Copyright (c) 2025, IT for Change and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Activity(Document):

    def before_save(self):
        if (self.activity_id is None):
            self.activity_id = self.name
