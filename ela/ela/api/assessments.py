import frappe
import requests


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

                    if (question.status == 'REPORT_COMPLETE'):
                        submission_doc.status = 'ASSESSED'
                        submission_doc.save()
                        continue
    return


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

    ela_get_api = doc.submission_list_callback
    ela_put_api = doc.submission_update_callback
    ela_add_file_api = doc.create_file_callback
    ela_api_host = doc.host
    ela_api_port = doc.port
    ela_image = doc.speech_separation
    ela_ai_install_dir = doc.ai_install_dir
    ela_api_token = doc.ela_api_token
    ela_activity = activity_id

    elamid_params = {
        'ela_image': ela_image,
        'ela_get_api': ela_get_api,
        'ela_put_api': ela_put_api,
        'ela_add_file_api': ela_add_file_api,
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
