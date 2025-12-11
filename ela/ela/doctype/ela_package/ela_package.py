# Copyright (c) 2025, ITFC and contributors
# For license information, please see license.txt

import zipfile
import xml.etree.ElementTree as ET
import os

# import frappe
import frappe
from frappe.model.document import Document


class ELAPackage(Document):

    def before_insert(self):

        attached_file_path = self.package
        absolute_file_path = frappe.get_site_path() + attached_file_path

        with zipfile.ZipFile(absolute_file_path, 'r') as zip_ref:
            extract_target_dir = frappe.get_site_path() + '/private/files/tmp/ela_packages'
            zip_ref.extractall(extract_target_dir)

        extracted_dir = os.path.abspath(extract_target_dir) + '/submissions'

        for filename in os.listdir(extracted_dir):

            if not filename.lower().endswith(".xml"):
                continue   # skip non-XML files

            file_path = os.path.join(extracted_dir, filename)
            tree = ET.parse(file_path)
            root = tree.getroot()
            asr = root.find('asr_collect_data')
            studentid = asr.find('studentid').text
            activityid = asr.find('activityid').text
            student_recording = asr.find('student_recording').text

            recording_to_attach = frappe.new_doc('File')
            # recording_to_attach.
            ela_submission = frappe.new_doc('ELA Submission')
            ela_submission.student = studentid
            ela_submission.activity = activityid
            ela_submission.audio_recording_file_path = os.path.join(
                extracted_dir, student_recording)
            ela_submission.insert()
