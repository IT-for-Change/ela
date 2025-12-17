# Copyright (c) 2025, ITFC and contributors
# For license information, please see license.txt

from datetime import datetime
import zoneinfo
import xml.sax.saxutils as saxutils
from jinja2 import Environment, FileSystemLoader

# import frappe
from frappe.model.document import Document
import frappe
from frappe.utils.jinja import render_template
from frappe.utils import slug


class AssessmentForm(Document):

    def before_save(self):

        configuration = frappe.get_doc('ELAConfiguration')
        template_config = configuration.supported_assessment_form_templates
        templates = template_config.split(',')

        questions = self.questions
        template = ''
        for question in questions:
            question_type = question.question_type
            template += question_type

        template = template.replace('AUDIO', 'A').replace(
            'SINGLE CHOICE', 'S').replace('MULTI CHOICE', 'M')

        if (template not in templates):
            frappe.throw(
                f"Unsupported question sequence or question types {template}")

        self.assessment_template_type = template

        if (self.form_id is None):
            self.form_id = self.name

        form_learners = frappe.get_all(
            'Learner',
            filters={'cohort': f'{self.cohort}'},
            fields=['name', 'name1', 'learner_id', 'display_name'],
            order_by='display_name asc'
        )

        form_teachers = frappe.get_all(
            'Teacher',
            fields=['name', 'name1', 'teacher_id', 'display_name'],
            order_by='display_name asc'
        )

        form_learner_cohort = frappe.get_doc(
            'Learner Cohort', self.cohort,
            fields=['cohort_name', 'name', 'learning_space', 'academic_year']
        )

        form_learning_space = frappe.get_doc(
            'Learning Space', form_learner_cohort.learning_space,
            fields=['name', 'name1', 'postal_code']
        )

        form_activity = frappe.get_doc('Activity', self.activity)

        questions = self.questions
        form_assessment_count = len(questions)
        form_assessment_ids = []
        form_question_types = []
        form_question_prompts = []
        form_question_titles = []
        form_question_actions = []
        form_all_choice_questions = []

        for index, question in enumerate(questions):
            question_index = index + 1
            question_type = question.question_type

            if (question_type == 'AUDIO'):
                form_question_type = question.audio_question_type

                if (form_question_type in ['SPEAKING', 'CONVERSATION']):
                    assessment = frappe.get_doc('Speaking Assessment', question.speaking_assessment, fields=[
                        'name', 'assessment_id'])

                    form_assessment_ids.append(assessment.assessment_id)

            if (question_type == 'SINGLE CHOICE'):
                assessment = frappe.get_doc('Single Choice Assessment', question.single_choice_assessment, fields=[
                    'name', 'assessment_id'])
                form_assessment_ids.append(assessment.assessment_id)
                choices_text = assessment.choices
                form_choices = {}
                for line in choices_text.splitlines():
                    key, value = line.split("|", 1)
                    form_choices[key.strip()] = value.strip()

                form_all_choice_questions.append(form_choices)

            form_question_types.append(question_type)
            question_prompt = question.prompt
            form_question_prompts.append(question_prompt)
            form_question_title = question.name
            form_question_titles.append(form_question_title)
            form_question_action = question.action_instruction
            form_question_actions.append(form_question_action)

        template_path = f"templates/{template}.xml"

        context = {
            "title": self.title,
            "id": self.form_id,
            "brief_note": self.brief_note,
            "cohort_id": form_learner_cohort.cohort_name,
            "learning_space_id": form_learning_space.name1,
            "activity_name": form_activity.activity_id,
            "activity_label": form_activity.title,
            "learners": form_learners,
            "teachers": form_teachers,
            "assessment_count": form_assessment_count,
            "assessment_ids": form_assessment_ids,
            # this section adds context for questions related text
            "question_types": form_question_types,
            "question_prompts": form_question_prompts,
            "question_titles": form_question_titles,
            "question_actions": form_question_actions,
            "all_choice_questions": form_all_choice_questions
        }

        output = frappe.render_template(template_path, context)

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
