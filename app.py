# A very simple Flask Hello World app for you to get started with...

import os
from flask import Flask, render_template, request
from Classes import XMLloader, NoteAnalysis, ScoreNotes

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/process_form', methods=['POST'])
def process_form():
    form_get = request.form
    # 调用 Python 函数
    scores, comments = nlp_process(form_get)
    return render_template('result.html', form_get=form_get, scores=scores, comments=comments)


def nlp_process(form_get):
    XML_setting = XMLloader('CHEST_PAIN.xml')
    keywords = XML_setting.get_keywords()
    applies_to = XML_setting.get_applies_to()
    note_analyzer = NoteAnalysis()
    results = []

    keywords_Q1 = keywords[:9]
    keywords_Q2 = keywords[9:12]
    keywords_Q3 = keywords[12:]
    applies_to_Q1 = applies_to[:9]
    applies_to_Q2 = applies_to[9:12]
    applies_to_Q3 = applies_to[12:]

    for key in form_get:
        text = form_get[key]
        text = text.lower()
        tokenized_text = note_analyzer.tokenize_text(text)
        tokenized_text_no_sw = note_analyzer.remove_stop_words(tokenized_text)
        stemmed_text = note_analyzer.stemming(tokenized_text_no_sw)
        removed_duplicates = note_analyzer.remove_duplicate_words(stemmed_text)

        if key == 'SCORATES':
            matched_contex = note_analyzer.keyword_context(text, applies_to_Q1)
            pc_keywords = note_analyzer.keyword_analysis(keywords_Q1, removed_duplicates, 80)
            result = {'keywords': pc_keywords, 'matched_context': matched_contex}
            results.append(result)

        if key == 'ICE':
            matched_contex = note_analyzer.keyword_context(text, applies_to_Q2)
            pc_keywords = note_analyzer.keyword_analysis(keywords_Q2, removed_duplicates, 80)
            result = {'keywords': pc_keywords, 'matched_context': matched_contex}
            results.append(result)

        if key == 'History':
            matched_contex = note_analyzer.keyword_context(text, applies_to_Q3)
            pc_keywords = note_analyzer.keyword_analysis(keywords_Q3, removed_duplicates, 80)
            result = {'keywords': pc_keywords, 'matched_context': matched_contex}
            results.append(result)

    feedback = []
    for result in results:
        score_notes = ScoreNotes(XML_setting)
        score_notes.compute_assignment_score(result)
        feedback.append(score_notes.compute_score())

    scores = []
    words = []

    for f in feedback:
        scores.append(f[0])
        words.append(f[1])

    comment = {}
    if scores[0] >= 8:
        comment[
            0] = ("A detailed description of the present illness, including a completed description of the chief "
                  "concerns,as well as good use of semantic and descriptive vocabulary. No lack of description of any "
                  "characteristic, keep up the good work!")

    elif 5 <= scores[0] <= 7:
        comment[
            0] = ("It seems that your description of the main complaint and symptoms is generally good but could "
                  "benefit from a bit more detail. You mentioned the key points such as the location and character of "
                  "the pain, but missing some aspects like: ") + ', '.join(
            words[0]) + ". Adding these details would provide a clearer picture of the patient's condition."

    elif 2 <= scores[0] <= 4:
        comment[
            0] = ("Incomplete description of the present illness, only including some of description of the chief "
                  "concerns, unsatisfactory use of semantic or descriptive vocabulary. Possible lack of description "
                  "of the following characteristics: ") + ', '.join(
            words[0]) + ". Improve them to make the record more complete."

    else:
        comment[
            0] = ("Poor description of the present illness, lack of most of the chief concerns, almost no use use of "
                  "semantic/descriptive vocabulary. Lack of the following characteristics: ") + ', '.join(
            words[0]) + ". Improve them to make the record more complete."

    if scores[1] == 3:
        comment[
            1] = ("Excellent use of the ICE framework. Clearly articulated patient's ideas, addressed their concerns "
                  "comprehensively, and managed their expectations effectively. The note demonstrates a strong "
                  "understanding of patient-centered care and ensures all aspects of the patient's perspective are "
                  "covered.")

    elif scores[1] == 2:
        comment[
            1] = ("Satisfactory application of the ICE framework. The note captures the patient’s ideas and some "
                  "concerns but could delve deeper into managing expectations. Overall, a solid effort with room for "
                  "improvement in ensuring all patient viewpoints are thoroughly explored. Possible lack of the "
                  "following points: ") + ', '.join(
            words[1]) + ". Improve them to modify the understanding of patient’s viewpoint."

    elif scores[1] == 1:
        comment[
            1] = ("Satisfactory application of the ICE framework. Overall, a solid effort with room for improvement in "
                  "ensuring all patient viewpoints are thoroughly explored. Possible lack of the following points: "
                  + ', '.join(
                    words[1]) + ". Improve them to modify the understanding of patient’s viewpoint.")

    else:
        comment[
            1] = ("Poor integration of the ICE framework. The note fails to adequately capture the patient’s ideas, "
                  "concerns, and expectations. It lacks depth and understanding of the patient's perspective, "
                  "leading to potential gaps in patient care and satisfaction.")

    if scores[2] == 4:
        comment[
            2] = ("Your abstraction of the patient's history is detailed and well-organized. You covered all relevant "
                  "aspects, including the past medical history, medication use, social habits, family history, "
                  "and so on. This comprehensive summary provides a clear and complete picture of the patient's "
                  "background, which is crucial for informed clinical decision-making.")

    elif 2 <= scores[2] <= 3:
        comment[
            2] = ("Overall complete and verified patient's history, it is generally accurate but could include a bit "
                  "more detail. Possible lack of the following history: ") + ', '.join(
            words[2]) + ". Providing a bit more information would enhance the completeness of the history."

    elif scores[2] == 1:
        comment[
            2] = ("Your summary of the patient's history is lacking in detail and important information. Key aspects "
                  "such as the following are missing: ") + ', '.join(
            words[2]) + ". Providing a bit more information would enhance the completeness of the history."

    else:
        comment[
            2] = ("Your summary of the patient's history is lacking in detail and important information. Key aspects "
                  "such as his past medical history, medication use, and social habits were not adequately covered. A "
                  "more thorough and organized approach is needed to ensure all relevant information is included.")

    scores[0] = int((scores[0] / 9) * 100)
    scores[1] = int((scores[1] / 3) * 100)
    scores[2] = int((scores[2] / 4) * 100)
    total_socre = int((scores[0] + scores[1] + scores[2]) / 3)
    scores.append(total_socre)

    if 80 <= total_socre <= 100:
        comment[
            3] = ("Your performance is excellent, showing a strong understanding and application of history taking and "
                  "symptom description skills. You have effectively used methods like SOCRATES to provide "
                  "comprehensive and detailed responses. Your ability to capture all relevant information about the "
                  "patient's history and symptoms is commendable. Continue to build on this strong foundation, "
                  "and consider exploring advanced techniques to further enhance your clinical skills. Your "
                  "proficiency in this area will serve you well in your medical career. Keep up the excellent work!")

    elif 60 <= total_socre <= 80:
        comment[
            3] = ("Your performance demonstrates a good grasp of history taking and symptom description. You have "
                  "successfully covered most key aspects, and your use of methods like SOCRATES is evident. However, "
                  "there are still some areas where you can improve to achieve a higher level of proficiency. Pay "
                  "attention to consistently capturing all relevant details and ensure that your responses are "
                  "well-organized and comprehensive. With continued practice and focus on refining your skills, "
                  "you can reach an excellent level of performance.")

    elif 40 <= total_socre <= 60:
        comment[
            3] = ("Your performance shows a basic understanding of the necessary skills for history taking and symptom "
                  "description, but there is still room for improvement. While you have covered some key aspects, "
                  "your responses might lack depth and completeness. Focus on improving the accuracy and detail of "
                  "your patient interviews. Practice using methods like SOCRATES more thoroughly and ensure that you "
                  "capture all relevant information about the patient's history and symptoms. With more practice and "
                  "attention to detail, you can significantly enhance your performance.")

    else:
        comment[
            3] = ("Your performance indicates that there are significant gaps in your understanding and application of "
                  "the necessary skills for history taking and symptom description. It is crucial to focus on "
                  "systematically using methods like SOCRATES to ensure comprehensive data collection. Consider "
                  "reviewing the fundamental principles of patient interviews and history taking, and practice more "
                  "to improve your skills. Consistent feedback and guidance from your instructors can help you "
                  "identify and work on your weak areas.")

    return scores, comment


if __name__ == '__main__':
    app.run()
