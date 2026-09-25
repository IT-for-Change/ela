import frappe
import traceback


def update_question_status(submission, entry_key, status):
    question_outputs = submission.response
    for index, question in enumerate(question_outputs):
        if question.type == 'AUDIO':
            if question.file == entry_key:
                question.status = status


def get_transcription_language(language_identification):

    transcription_language = language_identification['decision']
    score = language_identification['score']
    confidence = language_identification['confidence']
    remark = language_identification['remark']
    langid_decision_data = language_identification['langid_decision_data']
    return transcription_language, score, confidence, remark, langid_decision_data


def filter_question_for_curr_operation(question, operation):
    if (operation == "sdz" and question.status == "PENDING_LEARNER_SPEECH_SEPARATION"):
        return False
    if (operation == "langid" and question.status == "PENDING_LANGUAGE_CHECK"):
        return False
    if (operation == "stt" and question.status == "PENDING_TRANSCRIPTION"):
        return False
    if (operation == "nlp" and question.status == "PENDING_TEXT_ANALYSIS"):
        return False
    if (operation == "report" and question.status == "PENDING_REPORT"):
        return False

    return True


def get_assessment_question_for_output(question_output):
    question_index = int(question_output.question_index)
    assessment_form_id = question_output.assessment_form
    assessment_form_doc = frappe.get_doc(
        'Assessment Form', {"form_id": assessment_form_id})
    # index was stored as 1, 2 etc. when question output was extracted from package, but rows in child tables idx start 0.
    question = assessment_form_doc.questions[question_index - 1]
    return question


def get_assessment_question_text_assist_for_output(question_output):
    question = get_assessment_question_for_output(question_output)
    text_assist = question.text_assist
    return text_assist


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

        for index, question_output in enumerate(question_outputs):

            if (filter_question_for_curr_operation(question_output, operation) == True):
                continue

            # fetch the assessment for the question if the assessment entry already exists.
            # the assessment record might exist if the current status is anything other than the first step in the
            # assessment process, like "stt" if langid was done first, or 'langid' if speech separation was done first
            assessment_output_row = assessment_outputs_access_map.get(
                question_output.key_field, None)

            # return assessment_output_row.learner_speech_diarized

            if question_output.type == 'AUDIO':
                sdz = {
                    "source": f"{host}:{port}{question_output.file}",
                    "source_separation_ref": f"{host}:{port}{teacher_doc.voice_sample}"
                }
                langid = {
                    "language_candidates": f"{(learner_doc.primary_home_language).lower()}",
                    "learner_duration": assessment_output_row.learner_duration if assessment_output_row is not None else 0,
                    "teacher_duration": assessment_output_row.teacher_duration if assessment_output_row is not None else 0,
                    "source": f"{host}:{port}{frappe.get_doc('File',assessment_output_row.learner_speech_diarized).file_url}"
                    if assessment_output_row is not None
                    else f"{host}:{port}{question_output.file}"
                }
                stt = {
                    "language": assessment_output_row.transcription_language if assessment_output_row is not None else '',
                    "source": f"{host}:{port}{frappe.get_doc('File',assessment_output_row.learner_speech_diarized).file_url}"
                    if assessment_output_row is not None
                    else f"{host}:{port}{question_output.file}",
                    "langid_remark": assessment_output_row.transcription_language_remark if assessment_output_row is not None else '000',
                    "langid_score": assessment_output_row.language_id_score if assessment_output_row is not None else 0,
                    "langid_decision_data": assessment_output_row.langid_decision_data if assessment_output_row is not None else None,
                }
                nlp = {
                    "source": assessment_output_row.asr_text if assessment_output_row is not None else '',
                    "text_assist": get_assessment_question_text_assist_for_output(question_output),
                    "language": assessment_output_row.transcription_language if assessment_output_row is not None else '',
                    "grammar": "0"
                }
                report = {
                    "transcription_language": assessment_output_row.transcription_language if assessment_output_row is not None else '-',
                    "langid_score": assessment_output_row.language_id_score if assessment_output_row is not None else 0,
                    "transcription_language_remark": assessment_output_row.transcription_language_remark if assessment_output_row is not None else '000',
                    "asr_text": assessment_output_row.asr_text if assessment_output_row is not None else '',
                    "hallu_score":  assessment_output_row.hallu_score if assessment_output_row is not None else 0,
                    "word_count": assessment_output_row.word_count if assessment_output_row is not None else 0,
                    "lexical_density": assessment_output_row.lexical_density if assessment_output_row is not None else 0,
                    "text_analysis": assessment_output_row.nlp_text_analysis if assessment_output_row is not None else '',
                    "learner_duration": assessment_output_row.learner_duration if assessment_output_row is not None else 0,
                    "teacher_duration": assessment_output_row.teacher_duration if assessment_output_row is not None else 0
                }
                entry = {
                    "key": question_output.file,
                    "sdz": sdz,
                    "langid": langid,
                    "stt": stt,
                    "nlp": nlp,
                    "report": report
                }
            else:
                continue

            item_obj["entries"].append(entry)

        # submission should have at least one relevant entry, else filter out.
        if (len(item_obj["entries"]) != 0):
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
                language_identification = assessment_output["language_identification"]
                transcription_language, score, confidence, remark, langid_decision_data = get_transcription_language(
                    language_identification)
                if (assessment_output_row_does_not_exist):
                    submission.append("assessment_outputs", {
                        'key_field': key_field,
                        "langid_decision_data": str(langid_decision_data),
                        "transcription_language": transcription_language,
                        "language_id_score": score,
                        "transcription_language_remark": remark,
                        "confidence": confidence
                    })
                else:
                    assessment_output_row.langid_decision_data = str(
                        langid_decision_data)
                    assessment_output_row.transcription_language = transcription_language
                    assessment_output_row.language_id_score = score
                    assessment_output_row.confidence = confidence
                    assessment_output_row.transcription_language_remark = remark

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
                    # assessment_output_row.text_assist_similarity_score = transcription_output['text_assist_similarity_score']

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
                        "nlp_text_analysis": text_analysis_output,
                        "text_assist_similarity_score": transcription_output['text_assist_similarity_score'],
                        "text_assist_common_words": ", ".join(transcription_output['text_assist_common_words'])
                    })
                else:
                    assessment_output_row.nlp_text_analysis = text_analysis_output
                    assessment_output_row.word_count = text_analysis_output["token_count"]
                    assessment_output_row.lexical_density = text_analysis_output["lexical_density"]
                    assessment_output_row.text_assist_similarity_score = text_analysis_output.get(
                        "text_assist_similarity_score", 0)
                    assessment_output_row.text_assist_common_words = ", ".join(text_analysis_output.get(
                        "text_assist_common_words", ''))

                update_question_status(
                    submission, output["entry_key"], 'TEXT_ANALYSIS_COMPLETE')
                # update_question_status(
                # submission, output["entry_key"], 'REPORT_COMPLETE')

            if operation == "report":
                assessment_output = output["report"]
                report_output = assessment_output["report_outputs"]
                if (assessment_output_row_does_not_exist):
                    submission.append("assessment_outputs", {
                        "key_field": key_field,
                        "word_count": report_output["word_count"],
                        "lexical_density": report_output["lexical_density"],
                        "sixteen_point_score": report_output["sixteen_point_score"],
                        "conversation_contribution_pct": report_output["conversation_contribution_pct"],
                        "total_nouns": report_output["total_nouns"],
                        "total_proper_nouns": report_output["total_proper_nouns"],
                        "total_verbs": report_output["total_verbs"],
                        "total_adverbs": report_output["total_adverbs"],
                        "total_adjectives": report_output["total_adjectives"],
                        "total_prepositions": report_output["total_prepositions"],
                        "total_noun_phrases": report_output["total_noun_phrases"],
                        "total_clause_fragments": report_output["total_clause_fragments"],
                        "two_letter_words": report_output["two_letter_words"],
                        "three_letter_words": report_output["three_letter_words"],
                        "four_letter_words": report_output["four_letter_words"],
                        "five_letter_words": report_output["five_letter_words"],
                        "six_letter_words": report_output["six_letter_words"],
                        "seven_letter_words": report_output["seven_letter_words"],
                        "eight_letter_words": report_output["eight_letter_words"],
                        "nine_letter_words": report_output["nine_letter_words"],
                        "ten_letter_words": report_output["ten_letter_words"],
                        "greater_than_10_letter_words": report_output["greater_than_10_letter_words"],
                    })
                else:
                    assessment_output_row.word_count = report_output["word_count"]
                    assessment_output_row.lexical_density = report_output["lexical_density"]
                    assessment_output_row.sixteen_point_score = report_output["sixteen_point_score"]
                    assessment_output_row.conversation_contribution_pct = report_output[
                        "conversation_contribution_pct"]
                    assessment_output_row.total_nouns = report_output["total_nouns"]
                    assessment_output_row.total_proper_nouns = report_output["total_proper_nouns"]
                    assessment_output_row.total_verbs = report_output["total_verbs"]
                    assessment_output_row.total_adverbs = report_output["total_adverbs"]
                    assessment_output_row.total_adjectives = report_output["total_adjectives"]
                    assessment_output_row.total_prepositions = report_output["total_prepositions"]
                    assessment_output_row.total_noun_phrases = report_output["total_noun_phrases"]
                    assessment_output_row.total_clause_fragments = report_output[
                        "total_clause_fragments"]
                    assessment_output_row.two_letter_words = report_output["two_letter_words"]
                    assessment_output_row.three_letter_words = report_output["three_letter_words"]
                    assessment_output_row.four_letter_words = report_output["four_letter_words"]
                    assessment_output_row.five_letter_words = report_output["five_letter_words"]
                    assessment_output_row.six_letter_words = report_output["six_letter_words"]
                    assessment_output_row.seven_letter_words = report_output["seven_letter_words"]
                    assessment_output_row.eight_letter_words = report_output["eight_letter_words"]
                    assessment_output_row.nine_letter_words = report_output["nine_letter_words"]
                    assessment_output_row.ten_letter_words = report_output["ten_letter_words"]
                    assessment_output_row.greater_than_10_letter_words = report_output[
                        "greater_than_10_letter_words"]

                update_question_status(
                    submission, output["entry_key"], 'REPORT_COMPLETE')

            submission.save()
            frappe.db.commit()
    except Exception as e:
        # frappe.log_error(frappe.get_traceback(),"API Update Submissions Error")
        stack_trace = traceback.format_exc()
        frappe.log_error(stack_trace, "Update Submissions API Error")
        return {"status": "error", "message": e}
