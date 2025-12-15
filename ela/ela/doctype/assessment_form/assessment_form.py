# Copyright (c) 2025, ITFC and contributors
# For license information, please see license.txt

from datetime import datetime
import zoneinfo
import xml.sax.saxutils as saxutils

# import frappe
from frappe.model.document import Document
import frappe
from frappe.utils.jinja import render_template
from frappe.utils import slug


class AssessmentForm(Document):

    def before_save(self):

        learners = frappe.get_all(
            'Learner',
            filters={'cohort': f'{self.cohort}'},
            fields=['name', 'name1', 'learner_id', 'display_name']
        )

        teachers = frappe.get_all(
            'Teacher',
            fields=['name', 'name1', 'teacher_id', 'display_name']
        )

        learner_cohort = frappe.get_doc(
            'Learner Cohort', self.cohort,
            fields=['cohort_name', 'name', 'learning_space', 'academic_year']
        )

        learning_space = frappe.get_doc(
            'Learning Space', learner_cohort.learning_space,
            fields=['name', 'name1', 'postal_code']
        )

        questions = self.assessment_questions

        question_1_prompt = saxutils.escape(
            questions[0].question_prompt_rich_text)

        reading_assessment_options = saxutils.escape(
            questions[0].reading_assessment_options)

        activity_document = frappe.get_doc('Activity', self.activity)

        template_path = "ela/templates/odk_form_template_v2.xml"
        context = {
            "title": self.title,
            "id": self.name,
            "brief_instruction": self.brief_instruction,
            "cohort": learner_cohort.cohort_name,
            "learning_space": learning_space.name1,
            "activity_name": activity_document.name,
            "activity_label": activity_document.title,
            "learners": learners,
            "teachers": teachers,
            "question_1_prompt": question_1_prompt,
            "reading_assessment_options": reading_assessment_options
        }

        output = render_template(template_path, context)

        attachments = frappe.get_all('File', filters={
            'attached_to_name': self.name,
            "attached_to_doctype": 'Assessment Form'
        })

        if (len(attachments) > 0):
            form_file_old = frappe.delete_doc('File', attachments[0].name)

        file_name = slug(self.title).upper()

        file_doc = frappe.get_doc({
            "doctype": "File",
            # String that is your file's name
            "file_name": f'ELA-FORM-{file_name}.xml',
            "attached_to_doctype": 'Assessment Form',
            "attached_to_name": self.name,
            "is_private": True,
            "content": output,  # Your text/data content goes here.
            "folder": "Home"  # If you want to save in subdirectory, enter 'Home/MySubdirectory'
        }
        )
        file_doc.save()

        current_time = datetime.now(
            zoneinfo.ZoneInfo("Asia/Kolkata")).strftime("%H:%M:%S")

        current_date = datetime.now(
            zoneinfo.ZoneInfo("Asia/Kolkata")).strftime("%d-%b-%Y")

        self.form_last_generated = f'Form last generated at {current_time} on {current_date}'
