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
def display_assessment_block(activity_eid):

    submissions = frappe.get_list("Learner Submission",
                                  filters={
                                      'activity_eid': activity_eid})

    activity_doc = frappe.get_list(doctype="Activity", filters={
        'activity_id': activity_eid}, limit_page_length=1)

    if len(activity_doc) == 1:
        activity_doc = frappe.get_doc('Activity', activity_doc[0].name)
        # reset the child table.
        activity_doc.speech_separation = []
        activity_doc.save()

    # refresh submission status and also assessment log view in activity
    for submission in submissions:

        submission_doc = frappe.get_doc(
            'Learner Submission', submission.name)

        questions_output = submission_doc.response

        speech_separation_rows = []

        for index, question in enumerate(questions_output):

            if question.type == "AUDIO":

                assessment_doc = frappe.get_doc(
                    question.assessment_type, question.assessment)  # dynamic link in action!

                if (question.assessment_type == 'Speaking Assessment') and \
                    (assessment_doc.conversation == 1) and \
                        (question.status == None or question.status == 'CREATED'):

                    question.status = 'PENDING_LEARNER_SPEECH_SEPARATION'
                    submission_doc.save()

                    activity_doc.append("speech_separation", {
                        'submission': submission_doc.name,
                        'output': question,
                        'learner': submission_doc.learner,
                        'teacher': submission_doc.teacher_reference
                    })

    activity_doc.save()

    submissions_count = len(submissions)
    return submissions_count


@frappe.whitelist()
def run_assessment(activity_id):
    elamid_url = "http://elamid:80/run"

    ela_api = "ela.ela.doctype.activity.activity.get_submissions"
    ela_api_host = "elaexplore.localhost"
    ela_api_port = "8081"
    ela_activity = activity_id
    ela_image = "elastt:latest"
    params = {
        'ela_image': ela_image,
        'ela_activity': activity_id,
        'ela_api': ela_api,
        'ela_api_host': ela_api_host,
        'ela_api_port': ela_api_port
    }

    # Make the GET request to the external Flask API
    response = requests.get(elamid_url, params=params)

    # Check for successful response
    if response.status_code == 200:
        return response.text  # or any other type of response data you need
    else:
        # Handle API failure
        return f"Error: {response.status_code} - {response.text}"


@frappe.whitelist()
def get_submissions(activity_eid, reason):

    domain = frappe.utils.get_url()
    port = 8081
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
                    "source": f"{domain}:{port}{question.file}"
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
        # outputs = outputs.get('outputs', {})
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
