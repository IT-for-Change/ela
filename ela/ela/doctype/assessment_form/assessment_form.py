# Copyright (c) 2025, ITFC and contributors
# For license information, please see license.txt

from datetime import datetime
import zoneinfo


# import frappe
from frappe.model.document import Document
import frappe
from frappe.utils.jinja import render_template
from frappe.utils import slug


class AssessmentForm(Document):

    def before_save(self):

        learner_list = frappe.get_all(
            'Learner',
            filters={'cohort': f'{self.cohort}'},
            fields=['name1', 'learner_id', 'cohort']
        )

        questions = self.assessment_questions
        text = ''
        '''for question in questions:
            text += f'{question.response_type} | {question.mandatory} | {question.question_prompt_rich_text}'
        '''
        question_section_header = questions[0].response_type + ' Question'
        question_prompt = questions[0].question_prompt_rich_text
        activity_document = frappe.get_doc('Activity', self.activity)

        template_path = "library_management/templates/odk_form_v2.xml"
        context = {
            "title": self.title,
            "id": self.name,
            "cohort": self.cohort,
            "question_section_header": question_section_header,
            "question_prompt": question_prompt,
            "activity_label": activity_document.title,
            "activity_name": activity_document.name,
            "learners": str(learner_list),
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
