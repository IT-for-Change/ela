# Copyright (c) 2025, IT for Change and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ELAConfiguration(Document):
	def on_update(self):
		if not self.language_id_matrix:
			return

		file_doc = frappe.get_doc("File", {"file_url": self.language_id_matrix})
		if file_doc.is_private:
			file_doc.is_private = 0
			file_doc.save(ignore_permissions=True)
