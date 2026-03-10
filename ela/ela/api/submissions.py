import frappe


def update_question_status(submission, entry_key, status):
    question_outputs = submission.response
    for index, question in enumerate(question_outputs):
        if question.type == 'AUDIO':
            if question.file == entry_key:
                question.status = status


def get_transcription_language_reason(language, confidence):
    reason = "NOT_SPECIFIED"
    if language == '-':
        if confidence == 1:
            reason = 'LANGID_NO_SPEECH'
        else:
            reason = 'LANGID_INSUFFICIENT_SPEECH'
    else:
        if confidence >= 0.9:  # any valid detected language
            if language == 'en':
                reason = 'LANGID_ELAAI_CONFIRMED_EN'
            else:
                reason = 'LANGID_ELAAI_CONFIRMED_OTHER'
        else:  # valid detected language, but likely reported mixed
            if language == 'en':
                reason = 'LANGID_ELAAI_MIXED_EN'
            else:
                reason = 'LANGID_ELAAI_MIXED_OTHER'
    return reason


def get_transcription_language(languages_estimated):
    best_fit = max(languages_estimated, key=lambda x: x['confidence'])
    language = best_fit['language_code']
    confidence = best_fit['confidence']
    reason = get_transcription_language_reason(language, confidence)
    return language, confidence, reason


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

            if (filter_question_for_curr_operation(question, operation) == True):
                continue

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
                    "learner_duration": assessment_output_row.learner_duration if assessment_output_row is not None else 0,
                    "teacher_duration": assessment_output_row.teacher_duration if assessment_output_row is not None else 0,
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
                report = {
                    "transcription_language": assessment_output_row.transcription_language if assessment_output_row is not None else '-',
                    "transcription_language_reason": assessment_output_row.transcription_language_reason if assessment_output_row is not None else 'LANGID_NO_SPEECH',
                    "asr_text": assessment_output_row.asr_text if assessment_output_row is not None else '',
                    "hallu_score":  assessment_output_row.hallu_score if assessment_output_row is not None else 0,
                    "word_count": assessment_output_row.word_count if assessment_output_row is not None else 0,
                    "lexical_density": assessment_output_row.lexical_density if assessment_output_row is not None else 0,
                    "text_analysis": assessment_output_row.nlp_text_analysis if assessment_output_row is not None else '',
                    "learner_duration": assessment_output_row.learner_duration if assessment_output_row is not None else 0,
                    "teacher_duration": assessment_output_row.teacher_duration if assessment_output_row is not None else 0
                }
                entry = {
                    "key": question.file,
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
                languages_estimated = assessment_output["languages_estimation"]
                transcription_language, confidence, reason = get_transcription_language(
                    languages_estimated)
                if (assessment_output_row_does_not_exist):
                    submission.append("assessment_outputs", {
                        'key_field': key_field,
                        "languages_estimated": str(languages_estimated),
                        "transcription_language": transcription_language,
                        "transcription_language_reason": reason,
                        "confidence": round(confidence * 100, 1)
                    })
                else:
                    assessment_output_row.languages_estimated = str(
                        languages_estimated)
                    assessment_output_row.transcription_language = transcription_language
                    assessment_output_row.confidence = round(
                        confidence * 100, 1)
                    assessment_output_row.transcription_language_reason = reason

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
                        # "nine_point_score": "1.1",
                        "nlp_text_analysis": text_analysis_output
                    })
                else:
                    assessment_output_row.nlp_text_analysis = text_analysis_output
                    assessment_output_row.word_count = text_analysis_output["token_count"]
                    assessment_output_row.lexical_density = text_analysis_output["lexical_density"]
                    # assessment_output_row.nine_point_score = "1.1"

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
                        "nine_point_score_9": report_output["nine_point_score"],
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
                    assessment_output_row.nine_point_score_9 = report_output["nine_point_score"]
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
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}
