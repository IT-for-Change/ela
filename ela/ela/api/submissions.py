import frappe


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
                        "key_field": key_field,
                        "word_count": text_analysis_output["token_count"],
                        "lexical_density": text_analysis_output["lexical_density"],
                        "nine_point_score": "1.1",
                        "nlp_text_analysis": text_analysis_output
                    })
                else:
                    assessment_output_row.nlp_text_analysis = text_analysis_output
                    assessment_output_row.word_count = text_analysis_output["token_count"]
                    assessment_output_row.lexical_density = text_analysis_output["lexical_density"]
                    assessment_output_row.nine_point_score = "1.1"

                update_question_status(
                    submission, output["entry_key"], 'TEXT_ANALYSIS_COMPLETE')
                update_question_status(
                    submission, output["entry_key"], 'REPORT_COMPLETE')

            submission.save()
            frappe.db.commit()
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}
