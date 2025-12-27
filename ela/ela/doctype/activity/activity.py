# Copyright (c) 2025, IT for Change and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
import requests
import time


class Activity(Document):

    def before_save(self):
        if (self.activity_id is None):
            self.activity_id = self.name


@frappe.whitelist()
def display_assessment_block(activity_id):
    records = frappe.db.count('Learner Submission', {
        'status': 'Submitted', 'activity_eid': activity_id})
    # frappe.msgprint(f'found {records} submissions')
    time.sleep(10)
    return records


@frappe.whitelist()
def run_assessment(activity_id):
    api_url = "http://elamid:80/run"
    params = {'id': activity_id} if activity_id else {}

    # Make the GET request to the external Flask API
    response = requests.get(api_url, params=params)

    # Check for successful response
    if response.status_code == 200:
        return response.text  # or any other type of response data you need
    else:
        # Handle API failure
        return f"Error: {response.status_code} - {response.text}"
