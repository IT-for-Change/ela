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


def refresh_submission_status(submissions):

    submissions = frappe.get_list("Learner Submission",
                                  filters={'activity_eid': activity_eid})

    for submission in submissions:

        submission_doc = frappe.get_doc(
            'Learner Submission', submission.name)
        questions_output = submission_doc.response

        for index, question in enumerate(questions_output):

            if question.type == "AUDIO":

                assessment_doc = frappe.get_doc(
                    question.assessment_type, question.assessment)  # dynamic link in action!

                if (question.assessment_type == 'Speaking Assessment'):

                    if (question.status == None or question.status == 'CREATED'):
                        if (assessment_doc.conversation == 1):
                            question.status = 'PENDING_LEARNER_SPEECH_SEPARATION'
                            submission_doc.save()
                            continue
                        if (assessment_doc.detect_language == 1):
                            question.status = 'PENDING_LANGUAGE_CHECK'
                            submission_doc.save()
                            continue
                        # if nota, then set to proceed to transcription
                        question.status = 'PENDING_TRANSCRIPTION'
                        submission_doc.save()
                        continue

                    if (question.status == 'LEARNER_SPEECH_SEPARATION_COMPLETE'):
                        if (assessment_doc.detect_language == 1):
                            question.status = 'PENDING_LANGUAGE_CHECK'
                            submission_doc.save()
                            continue
                        else:
                            question.status = 'PENDING_TRANSCRIPTION'
                            submission_doc.save()
                            continue

                    if (question.status == 'LANGUAGE_CHECK_COMPLETE'):
                        question.status = 'PENDING_TRANSCRIPTION'
                        submission_doc.save()
                        continue

                    if (question.status == 'TRANSCRIPTION_COMPLETE'):
                        question.status = 'PENDING_TEXT_ANALYSIS'
                        submission_doc.save()
                        continue

                    if (question.status == 'TEXT_ANALYSIS_COMPLETE'):
                        question.status = 'PENDING_REPORT'
                        submission_doc.save()
                        continue


def update_activity_assessment_log_view(submissions, activity_eid):

    activity_doc = frappe.get_list(doctype="Activity", filters={
        'activity_id': activity_eid}, limit_page_length=1)

    if len(activity_doc) == 1:
        activity_doc = frappe.get_doc('Activity', activity_doc[0].name)
        # reset the child tables.
        activity_doc.speech_separation = []
        activity_doc.language_identification = []
        activity_doc.transcription = []
        activity_doc.text_analysis = []
        activity_doc.report = []
        activity_doc.save()

    for submission in submissions:

        submission_doc = frappe.get_doc(
            'Learner Submission', submission.name)

        questions_output = submission_doc.response

        for index, question in enumerate(questions_output):

            ui_assessment_log_name = ''  # this will hold the assessment log UI child table name
            submission_entry = {}
            submission_entry['submission']: submission_doc.name
            submission_entry['output']: question
            submission_entry['learner']: submission_doc.learner
            submission_entry['teacher']: submission_doc.teacher_reference

            if question.status == 'PENDING_LEARNER_SPEECH_SEPARATION':
                ui_assessment_log_name = "speech_separation"
            if question.status == 'PENDING_LANGUAGE_CHECK':
                ui_assessment_log_name = "language_identification"
            if question.status == 'PENDING_TRANSCRIPTION':
                ui_assessment_log_name = "transcription"
            if question.status == 'PENDING_TEXT_ANALYSIS':
                ui_assessment_log_name = "text_analysis"
            if question.status == 'PENDING_REPORT':
                ui_assessment_log_name = "report"

            activity_doc.append(assessment_type_name, submission_entry)

    activity_doc.save()


@frappe.whitelist()
def display_assessment_block(activity_eid):

    # update submission docs status for next action based on previous action done via elamid
    refresh_submission_status(submissions)
    # update UI view in activity
    update_activity_assessment_log_view(submissions, activity_doc)

    submissions_count = len(submissions)
    return submissions_count


@frappe.whitelist()
def run_assessment(activity_id, operation):

    doc = frappe.get_doc('ELA Configuration')
    elamid_url = doc.middleware_endpoint

    ela_api = doc.speech_separation_callback
    ela_api_host = doc.host
    ela_api_port = doc.port
    ela_image = doc.speech_separation
    ela_activity = activity_id
    elamid_params = {
        'ela_image': ela_image,
        'ela_activity': activity_id,
        'ela_api': ela_api,
        'ela_api_host': ela_api_host,
        'ela_api_port': ela_api_port
    }

    response = requests.get(elamid_url, params=elamid_params)

    if response.status_code == 200:
        return response.text
    else:
        return f"Error: {response.status_code} - {response.text}"


@frappe.whitelist()
def get_submissions(activity_eid, reason):

    doc = frappe.get_doc('ELA Configuration')
    host = doc.host
    port = doc.port
    response = {"items": []}

    submissions = frappe.get_list("Learner Submission",
                                  filters={
                                      'activity_eid': activity_eid})

    for submission in submissions:
        doc = frappe.get_doc("Learner Submission", submission)
        item_obj = {
            "item_key": submission,
            "entries": []
        }
        question_outputs = doc.response
        for index, question in enumerate(question_outputs):
            if question.type == 'AUDIO':
                entry_obj = {
                    "entry_key": question.file,
                    "language": "en",
                    "source": f"{host}:{port}{question.file}"
                }
            else:
                continue
            item_obj["entries"].append(entry_obj)

        response["items"].append(item_obj)

    return response


@frappe.whitelist()
def update_submissions(outputs):

    try:
        outputs = frappe.parse_json(outputs)

        for index, output in enumerate(outputs):
            learner_submission_id = output["item_key"]
            audio_file = output["entry_key"]
            asr_text = output["asr_text"]
            language = output["language"]
            confidence = output["confidence"]
            submission = frappe.get_doc(
                "Learner Submission", learner_submission_id)
            submission.append("assessment_outputs", {
                "language_identified": language,
                "confidence": confidence,
                "learner_contribution": audio_file,
                "asr_text": asr_text
            })
            submission.save()
            frappe.db.commit()
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}
