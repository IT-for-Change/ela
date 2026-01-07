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


def refresh_submission_status(activity_eid):

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
                            # frappe.msgprint(
                            # f'{submission_doc.name} is pending speech separation')
                            continue
                        if (assessment_doc.conversation == 0):
                            if (assessment_doc.detect_language == 1):
                                question.status = 'PENDING_LANGUAGE_CHECK'
                                submission_doc.save()
                                continue
                            else:
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


def update_activity_assessment_log_view(activity_eid):

    submissions = frappe.get_list("Learner Submission",
                                  filters={'activity_eid': activity_eid})

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

            # this will hold the assessment log UI child table name
            ui_assessment_log_name = 'NA'
            submission_entry = {}
            submission_entry['submission'] = submission_doc.name
            submission_entry['output'] = question
            submission_entry['learner'] = submission_doc.learner
            submission_entry['teacher'] = submission_doc.teacher_reference

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

            activity_doc.append(ui_assessment_log_name, submission_entry)

    activity_doc.save()

    count_speech_separation = len(activity_doc.speech_separation)
    count_language_check = len(activity_doc.language_identification)
    count_transcription = len(activity_doc.transcription)
    count_text_analysis = len(activity_doc.text_analysis)
    count_report = len(activity_doc.report)

    return {
        'count_speech_separation': count_speech_separation,
        'count_language_check': count_language_check,
        'count_transcription': count_transcription,
        'count_text_analysis': count_text_analysis,
        'count_report': count_report,
        'total_pending': count_speech_separation +
        count_language_check +
        count_transcription +
        count_text_analysis +
        count_report
    }


@frappe.whitelist()
def display_assessment_block(activity_eid):

    # update submission docs status for next action based on previous action done via elamid
    submissions_count = refresh_submission_status(activity_eid)
    # update UI view in activity
    count_stats = update_activity_assessment_log_view(activity_eid)

    return count_stats


@frappe.whitelist()
def run_assessment(activity_id, operation):

    doc = frappe.get_doc('ELAConfiguration')
    elamid_url = doc.middleware_endpoint

    ela_api = doc.speech_separation_callback
    ela_api_host = doc.host
    ela_api_port = doc.port
    ela_image = doc.speech_separation
    ela_ai_install_dir = doc.ai_install_dir
    ela_api_token = doc.ela_api_token
    ela_activity = activity_id

    elamid_params = {
        'ela_image': ela_image,
        'ela_api': ela_api,
        'ela_api_host': ela_api_host,
        'ela_api_port': ela_api_port,
        'ela_ai_install_dir': ela_ai_install_dir,
        'ela_ai_operation': operation,
        'ela_activity': ela_activity,
        'ela_api_token': ela_api_token
    }

    response = requests.get(elamid_url, params=elamid_params)
    if response.status_code == 200:
        return response.text
    else:
        return f"Error: {response.status_code} - {response.text}"


@frappe.whitelist()
def get_submissions(activity_eid, operation):

    doc = frappe.get_doc('ELAConfiguration')
    host = doc.host
    port = doc.port
    response = {"items": []}

    submissions = frappe.get_list("Learner Submission",
                                  filters={
                                      'activity_eid': activity_eid})

    for submission in submissions:
        doc = frappe.get_doc("Learner Submission", submission)
        teacher_doc = frappe.get_doc("Teacher", doc.teacher_reference)
        learner_doc = frappe.get_doc("Learner", doc.learner)
        item_obj = {
            "item_key": submission,
            "entries": []
        }
        question_outputs = doc.response
        for index, question in enumerate(question_outputs):
            if question.type == 'AUDIO':
                stt = {
                    "language": "EN",
                    "source": f"{host}:{port}{question.file}"
                }
                lang_check = {
                    "language_candidate_s": f"EN,{learner_doc.primary_home_language}",
                    "source": f"{host}:{port}{question.file}"
                }
                sdz = {
                    "source": f"{host}:{port}{question.file}",
                    "source_separation_ref": f"{host}:{port}{teacher_doc.voice_sample}"
                }
                nlp = {
                    "source": "<asr_text>",
                    "grammar": "1"
                }
                entry_obj = {
                    "key": question.file,
                    "sdz": sdz,
                    "lang_check": lang_check,
                    "stt": stt,
                    "nlp": nlp
                }
            else:
                continue
            item_obj["entries"].append(entry_obj)

        response["items"].append(item_obj)

    return response


def update_question_status(submission, entry_key, status):
    question_outputs = submission.response
    for index, question in enumerate(question_outputs):
        if question.type == 'AUDIO':
            if question.file == entry_key:
                question.status = status


@frappe.whitelist()
def update_submissions(outputs, operation):

    try:
        outputs = frappe.parse_json(outputs)
        for index, output in enumerate(outputs):
            learner_submission_id = output["item_key"]
            submission = frappe.get_doc(
                "Learner Submission", learner_submission_id)
            assessment_output = {}
            if operation == "sdz":
                assessment_output = output["sdz"]
                learner_duration = assessment_output['learner_duration']
                learner_max_duration = assessment_output['learner_max_duration']
                teacher_duration = assessment_output['teacher_duration']
                teacher_max_duration = assessment_output['teacher_max_duration']
                total_turns = assessment_output['total_turns']
                audio_fileid_learner = assessment_output['audio_fileid_learner']
                # TODO - submission assessment_outputs reset before appending new.
                submission.append("assessment_outputs", {
                    'audio_response_recording': output["entry_key"],
                    'learner_duration': learner_duration,
                    'learner_duration_max': learner_max_duration,
                    'teacher_duration': teacher_duration,
                    'teacher_duration_max': teacher_max_duration,
                    'total_turns': total_turns,
                    'learner_speech_diarized': audio_fileid_learner
                })
                update_question_status(
                    submission, output["entry_key"], 'LEARNER_SPEECH_SEPARATION_COMPLETE')

            if operation == "stt":
                asr_text = output["asr_text"]
                language = output["language"]
                confidence = output["confidence"]

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
