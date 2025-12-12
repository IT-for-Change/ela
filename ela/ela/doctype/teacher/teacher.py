# Copyright (c) 2025, IT for Change and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Teacher(Document):

    def before_insert(self):
        self.display_name = f'{self.name1} ({self.teacher_id})'

    def on_update(self):
        self.display_name = f'{self.name1} ({self.teacher_id})'
