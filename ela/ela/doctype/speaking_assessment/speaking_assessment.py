# Copyright (c) 2025, IT for Change and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SpeakingAssessment(Document):

    def before_save(self):
        if (self.assessment_id is None):
            self.assessment_id = self.name
