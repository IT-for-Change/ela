# Copyright (c) 2025, IT for Change and contributors
# For license information, please see license.txt

import zipfile
import io
from io import BytesIO
import xml.etree.ElementTree as ET

# import frappe
from frappe.model.document import Document
import frappe


class AssessmentPackage(Document):

    def after_insert(self):

        if (self.package_file == None):
            return

        package_format = self.package_format

        package_file = frappe.get_doc("File", {"file_url": self.package_file})
        # IMP: the 'file_name' field of File doctype holds the unaltered (original) file name.
        uploaded_file_name = package_file.file_name

        content = package_file.get_content()

        num_submissions = 0
        audio_files_mapping = {}
        # unique_ela_forms = []
        # Read zip and contents directly into memory. Avoid creating tmp files, dirs.
        with zipfile.ZipFile(BytesIO(content), 'r') as zip:
            file_names = zip.namelist()
            # Read the content of each file directly into memory
            for file_name in file_names:
                if file_name.endswith('.m4a'):
                    with zip.open(file_name) as file:
                        file_contents = file.read()
                        file_name_unqualified = file_name.split("/")[-1]
                        file_doc = frappe.get_doc({
                            "doctype": 'File',
                            "file_name": file_name_unqualified,
                            "content": file_contents,
                            "folder": "Home"
                        })
                        file_doc.save()

                    audio_files_mapping[file_name_unqualified] = file_doc.file_url

            for file_name in file_names:
                if file_name.endswith('.xml'):
                    num_submissions += 1
                    with zip.open(file_name) as file:
                        file_contents = file.read()
                        self.create_submission(
                            file_contents, audio_files_mapping)

        # self.assessment_forms_in_package = str(set(unique_ela_forms))
        self.status = 'Ready'
        self.save()

    def get_assessment_doc(self, assessment_id):

        possible_doctypes = ["Speaking Assessment", "Readabout Assessment",
                             "Writing Assessment", "Single Choice Assessment", "Multi Choice Assessment"]

        for dt in possible_doctypes:
            if frappe.db.exists({"doctype": dt, "assessment_id": assessment_id}):
                doc = frappe.get_doc(dt, {'assessment_id': assessment_id}, [
                                     'name', 'assessment_id'])
                return dt, doc

        return None, None

    def create_submission(self, xml_string, audio_files_mapping):
        root = ET.fromstring(xml_string)

        # 1) Extract and print required fields
        start_time = root.findtext("startTime")
        ela_form_id = root.findtext("form_introduction/ela_form_id")
        num_assessments = int(root.findtext(
            "form_introduction/num_assessments"))
        learner = root.findtext("form_configuration/learner")
        teacher = root.findtext("form_configuration/teacher")
        activity = root.findtext("form_configuration/activity")

        learner_doc = frappe.get_value('Learner', {"learner_id": learner},
                                       ['name', 'name1',
                                       'learner_id', 'display_name', "cohort"], as_dict=True
                                       )

        activity_doc = frappe.get_doc('Activity', {'activity_id': activity},
                                      ['name', 'name1', 'activity_id', 'title'], as_dict=True)

        activity_in_package = frappe.new_doc("Activity in Package")
        activity_in_package.activity = activity_doc.name
        self.activities_in_package.append(activity_in_package)

        # Loop through assessments
        question_outputs_list = []
        for index in range(1, num_assessments + 1):
            question_output = {}
            question_output_doc_file_name = 'Question Output'
            question_output['doctype'] = question_output_doc_file_name
            assessment_id = root.findtext(
                f"question_{index}/assessment_id_{index}")
            assessment_type, assessment_doc = self.get_assessment_doc(
                assessment_id)
            question_type = root.findtext(
                f"question_{index}/question_{index}_type")

            question_output['assessment_type'] = assessment_type
            question_output['assessment'] = assessment_doc.name
            frappe.msgprint(f'{assessment_type}:{assessment_doc.name}')
            # frappe.get_doc('DocType')
            question_output['type'] = question_type

            response = None
            if question_type == "AUDIO":
                response = root.findtext(
                    f"question_{index}/question_{index}_audio")
                audio_file_url = audio_files_mapping[response]
                question_output['file'] = audio_file_url
            elif question_type == "SINGLE CHOICE":
                response = root.findtext(
                    f"question_{index}/question_{index}_singlechoice")
                question_output['response'] = response

            question_outputs_list.append(question_output)

        submission = frappe.get_doc({
            'doctype': 'Learner Submission',
            'submitted_datetime': start_time,
            'submitted_via_form': ela_form_id,
            'source_package': self.name,
            "learner": learner_doc.name,
            "learner_display_name": learner_doc.display_name,
            "learner_cohort": learner_doc.cohort,
            "activity_reference": activity_doc.name,
            "activity_title": activity_doc.title,
            "activity_eid": activity_doc.activity_id,
            "response": question_outputs_list
        })

        submission.insert()
