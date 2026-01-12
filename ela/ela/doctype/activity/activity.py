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
                                      'activity_eid': activity_eid},
                                  order_by="creation asc")

    for submission in submissions:
        doc = frappe.get_doc("Learner Submission", submission)
        teacher_doc = frappe.get_doc("Teacher", doc.teacher_reference)
        learner_doc = frappe.get_doc("Learner", doc.learner)
        item_obj = {
            "item_key": submission,
            "entries": []
        }
        question_outputs = doc.response  # child table
        assessment_outputs = doc.assessment_outputs  # child table
        # create easy access dicts to lookup rows in each of the child tables based on the common unique key
        # common unique key is the field imaginatively called 'key_field'. For 'AUDIO', this value is populated with
        # the audio recording filename. TODO - figure out what the unique key field should be for non audio questions.
        question_outputs_access_map = {
            question.key_field: question for question in question_outputs
        }
        assessment_outputs_access_map = {
            assessment_output.key_field: assessment_output for assessment_output in assessment_outputs
        }

        for index, question in enumerate(question_outputs):
            # fetch the assessment for the question if the assessment entry already exists.
            # the assessment record might exist if the current status is anything other than the first step in the
            # assessment process, like "stt" if langid was done first, or 'langid' if speech separation was done first
            assessment_output_row = assessment_outputs_access_map.get(
                question.key_field, None)

            # return assessment_output_row.learner_speech_diarized

            if question.type == 'AUDIO':
                sdz = {
                    "source": f"{host}:{port}{question.file}",
                    "source_separation_ref": f"{host}:{port}{teacher_doc.voice_sample}"
                }
                langid = {
                    "language_candidates": f"{(learner_doc.primary_home_language).lower()}",
                    "source": f"{host}:{port}{frappe.get_doc('File',assessment_output_row.learner_speech_diarized).file_url}"
                    if assessment_output_row is not None
                    else f"{host}:{port}{question.file}"
                }
                stt = {
                    "language": assessment_output_row.transcription_language if assessment_output_row is not None else '',
                    "source": f"{host}:{port}{frappe.get_doc('File',assessment_output_row.learner_speech_diarized).file_url}"
                    if assessment_output_row is not None
                    else f"{host}:{port}{question.file}"
                }
                nlp = {
                    "source": assessment_output_row.asr_text if assessment_output_row is not None else '',
                    "language": assessment_output_row.transcription_language if assessment_output_row is not None else '',
                    "grammar": "0"
                }
                entry_obj = {
                    "key": question.file,
                    "sdz": sdz,
                    "langid": langid,
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


def get_transcription_language(languages_estimated):
    best_fit = max(languages_estimated, key=lambda x: x['confidence'])
    language = best_fit['language_code']
    confidence = best_fit['confidence']
    return language, confidence


@frappe.whitelist()
def update_submissions(outputs, operation):

    try:
        outputs = frappe.parse_json(outputs)
        for index, output in enumerate(outputs):
            learner_submission_id = output["item_key"]
            submission = frappe.get_doc(
                "Learner Submission", learner_submission_id)
            # load existing assessment_outputs, otherwise new rows will end up getting inserted for each submission's update
            assessment_outputs = submission.assessment_outputs
            assessment_outputs_access_map = {
                assessment_output.key_field: assessment_output for assessment_output in assessment_outputs
            }

            key_field = output["entry_key"]
            assessment_output_row = assessment_outputs_access_map.get(
                key_field, None)

            assessment_output_row_does_not_exist = True if assessment_output_row is None else False

            if operation == "sdz":

                assessment_output = output["sdz"]
                learner_duration = assessment_output['learner_duration']
                learner_max_duration = assessment_output['learner_max_duration']
                teacher_duration = assessment_output['teacher_duration']
                teacher_max_duration = assessment_output['teacher_max_duration']
                total_turns = assessment_output['total_turns']
                audio_fileid_learner = assessment_output['audio_fileid_learner']

                if (assessment_output_row_does_not_exist):
                    submission.append("assessment_outputs", {
                        'key_field': key_field,
                        'audio_response_recording': key_field,
                        'learner_duration': learner_duration,
                        'learner_duration_max': learner_max_duration,
                        'teacher_duration': teacher_duration,
                        'teacher_duration_max': teacher_max_duration,
                        'total_turns': total_turns,
                        'learner_speech_diarized': audio_fileid_learner
                    })
                else:
                    assessment_output_row.learner_duration = learner_duration
                    assessment_output_row.learner_duration_max = learner_max_duration
                    assessment_output_row.teacher_duration = teacher_duration
                    assessment_output_row.teacher_duration_max = teacher_max_duration
                    assessment_output_row.total_turns = total_turns
                    assessment_output_row.learner_speech_diarized = audio_fileid_learner

                update_question_status(
                    submission, output["entry_key"], 'LEARNER_SPEECH_SEPARATION_COMPLETE')

            if operation == "langid":

                assessment_output = output["langid"]
                languages_estimated = assessment_output["languages_estimation"]
                transcription_language, confidence = get_transcription_language(
                    languages_estimated)
                if (assessment_output_row_does_not_exist):
                    submission.append("assessment_outputs", {
                        'key_field': key_field,
                        "languages_estimated": str(languages_estimated),
                        "transcription_language": transcription_language,
                        "confidence": round(confidence * 100, 1)
                    })
                else:
                    assessment_output_row.languages_estimated = str(
                        languages_estimated)
                    assessment_output_row.transcription_language = transcription_language
                    assessment_output_row.confidence = round(
                        confidence * 100, 1)

                update_question_status(
                    submission, output["entry_key"], 'LANGUAGE_CHECK_COMPLETE')

            if operation == "stt":

                assessment_output = output["stt"]
                transcription_output = assessment_output["transcription_output"]
                if (assessment_output_row_does_not_exist):
                    submission.append("assessment_outputs", {
                        'key_field': key_field,
                        "asr_text": transcription_output['asr_text'],
                        "hallu_score": transcription_output['hallu_score'],
                        "hallu_text": str(transcription_output['hallu_text'])
                    })
                else:
                    assessment_output_row.asr_text = transcription_output['asr_text']
                    assessment_output_row.hallu_score = transcription_output['hallu_score']
                    assessment_output_row.hallu_text = str(
                        transcription_output['hallu_text'])

                update_question_status(
                    submission, output["entry_key"], 'TRANSCRIPTION_COMPLETE')

            if operation == "nlp":
                assessment_output = output["nlp"]
                text_analysis_output = assessment_output["analyzed_text"]
                if (assessment_output_row_does_not_exist):
                    submission.append("assessment_outputs", {
                        'key_field': key_field,
                        "nlp_text_analysis": text_analysis_output
                    })
                else:
                    assessment_output_row.nlp_text_analysis = text_analysis_output

                update_question_status(
                    submission, output["entry_key"], 'TEXT_ANALYSIS_COMPLETE')

            submission.save()
            frappe.db.commit()
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}
