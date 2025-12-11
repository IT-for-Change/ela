# Copyright (c) 2025, ITFC and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Learner(Document):
    pass

    def before_insert(self):
        self.display_name = f'{self.name1} ({self.learner_id})'

    def on_update(self):
        self.display_name = f'{self.name1} ({self.learner_id})'
