import ntpath
import string
import nltk
import os, sys
from docx import Document
from fuzzywuzzy import fuzz
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer
import xml.etree.ElementTree as et


class FileLoader:
    def __init__(self, folder_selected):
        """Initialization function."""
        self.folder_selected = folder_selected
        self.file_list = []

    def get_files(self):
        """Returns the files as a list."""

        for path, subdirs, files in os.walk(self.folder_selected):
            for name in files:
                if name.endswith('.docx'):
                    self.file_list.append(os.path.join(path, name))
        return self.file_list


class ParagraphParser:
    """Add document paragraphs to list object."""

    def __init__(self):
        self.document_paragraphs = []

    def get_paragraphs(self, document_list):
        """Return the documents and associated paragraphs."""
        for file in document_list:
            doc = Document(file)
            for paragraph in doc.paragraphs:
                self.document_paragraphs.append(paragraph.text)
        return self.document_paragraphs


class XMLloader:
    def __init__(self, note_data_file_xml):
        self.GP_Notes = []
        self.marks_per_concept = []
        self.keywords = []
        self.applies_to = []
        self.applies_to_concept = []
        self.applies_list = []
        self.filename = note_data_file_xml
        try:
            self.content = et.parse(self.filename)
            self.root = self.content.getroot()
        except:
            print("Error parsing file:", self.filename)
            sys.exit(1)

        self.number_of_concepts = len(self.root.findall('concept'))
        self.concept_titles = []
        v = []
        for concept in self.root.iter('concept'):
            self.marks_per_concept.append(float(concept.attrib['max_marks']))
            self.keywords.append([i.text for i in concept.iter('keyword')])
            self.concept_titles.append([i.text for i in concept.iter('title')])

            for ap in concept.iter('applies'):
                vals = ap.attrib.values()
                vals_list = list(vals)
                v.append(vals_list[0])
                st_list = [i.lstrip() for i in ap.text.split(',')]
                self.applies_to.append({vals_list[0]: tuple(st_list)})

            self.applies_list.append(v)
            v = []
            self.applies_to_concept.append(self.applies_to)
            self.applies_to = []

    def add_GP_notes(self, notes):
        """Create a list of individual GP note objects."""
        for note_file in notes:
            current_note = GPNote(note_file)
            self.GP_Notes.append(current_note)

    def get_GP_notes(self):
        """Return the list of GP notes."""
        return self.GP_Notes

    def get_keywords(self):
        """Return the list of keywords."""
        return self.keywords

    def get_applies_to(self):
        """Return the applies to context."""
        return self.applies_to_concept

    def get_applies_keywords(self):
        """Return the list of applies keys."""
        return self.applies_list


class GPNote:
    def __init__(self, note_file):
        self.note_file = note_file
        self.note_mark_pc = 0
        self.keyword_score = 0
        self.context_score = 0
        self.concept_scores = []
        self.student_feedback = ""
        paragraph_parser = ParagraphParser()
        self.paragraph_list = paragraph_parser.get_paragraphs([self.note_file])

    def path_leaf(self, file_path):
        """Function to return just filename from file path."""
        head, tail = ntpath.split(file_path)
        return tail.split('.', 1)[0] or ntpath.basename(head).split('.', 1)[0]


class NoteAnalysis:
    def __init__(self):
        self.keyword_fuzz_ratios = []

    def tokenize_text(self, assignment_text):
        """Split text into words, remove punctuation."""
        word_tokens = word_tokenize(assignment_text)
        words = [word for word in word_tokens if word.isalpha()]
        return words

    def remove_stop_words(self, assignment_text):
        """Remove all stop words form text."""
        stop_words = set(stopwords.words('english'))
        words = [i for i in assignment_text if not i in stop_words]
        return words

    def stemming(self, word_list):
        """Remove all the duplicate words from text for keyword matching."""
        ps = PorterStemmer()
        stemmed_list =  [ps.stem(word) for word in word_list]
        return stemmed_list
    def remove_duplicate_words(self, assignment_text):
        """Remove all the duplicate words from text for keyword matching."""
        filtered_list = []
        for word in assignment_text:
            if word not in filtered_list:
                filtered_list.append(word)
        return filtered_list

    def keyword_analysis(self, keywords, assignment_text, keyword_ratio=80, echo=False):
        """Match keywords using fuzzy strings."""
        word_matched = 0
        concept_matches = []
        self.keyword_ratio = keyword_ratio
        for keywords_in_concept in keywords:
            for keyword in keywords_in_concept:
                for word in assignment_text:
                    ratio = fuzz.ratio(word, keyword)
                    if ratio >= self.keyword_ratio:
                        word_matched = word_matched + 1
                        if echo:
                            print("Matched (word/kw): ", word, keyword, ratio)
                        self.keyword_fuzz_ratios.append({'word': word, 'keyword': keyword, 'fuzzy-ratio': ratio})
            if word_matched > 0 and word_matched < len(keywords_in_concept):
                concept_matches.append((word_matched / len(keywords_in_concept)) * 100)
            elif word_matched > 0 and word_matched >= len(keywords_in_concept):
                concept_matches.append(100)
            elif word_matched == 0:
                concept_matches.append(word_matched)
            word_matched = 0
        return tuple(concept_matches)

    """Code taken from……"""
    def keyword_context(self, assignment_text, applies_to, match_ratio=80):
        """Fuzzy match bi-grams."""
        matched_bigrams = []
        bigrams_per_context = []
        for applied_context in applies_to:
            assignment_text_no_punctuation = assignment_text.translate(str.maketrans('', '', string.punctuation))
            nltk_tokens = nltk.word_tokenize(assignment_text_no_punctuation)
            kc_bigrams = list(nltk.bigrams(nltk_tokens))
            for key_context in applied_context:
                for key, value in key_context.items():
                    for item in value:
                        for gram in kc_bigrams:
                            r1 = fuzz.ratio(key, gram[0])
                            r2 = fuzz.ratio(item, gram[1])
                            if r1 >= match_ratio and r2 >= match_ratio:
                                matched_bigrams.append(
                                    {'term_1': key, 'bigram_1': gram[0], 'term_2': item, 'bigram_2': gram[1],
                                     'ratio_1': r1, 'ratio_2': r2})
            bigrams_per_context.append(matched_bigrams)
            matched_bigrams = []
        return bigrams_per_context


class ScoreNotes:
    def __init__(self, XML_object):
        self.concept_scores = []
        self.XML_setting_object = XML_object
        self.score = 0
        self.SOCRATES = ['Main', 'Site', 'Onset', 'Character', 'Radiation', 'Associated Symptoms', 'Timing',
                         'Exacerbating and Relieving Factors', 'Severity']
        self.ICE = ['Ideas', 'Concerns', 'Expectations']
        self.PH = ['Medical History', 'Drug History and Allergies', 'Family History', 'Social History']
        self.excluded = []

    def compute_assignment_score(self, results):
        """Process the results to extract final scores and add to individual assignment."""
        if 'matched_context' in results.keys():
            ap_keywords = self.XML_setting_object.get_applies_keywords()
            keys_to_match_per_concept = [len(i) for i in ap_keywords]
            concept_matches = [len(i) for i in results['matched_context']]
            match_pc = []

            if len(concept_matches) == 9:
                for i, j in zip(keys_to_match_per_concept[0:9], concept_matches):
                    match_pc.append((j / i) * 100)
            elif len(concept_matches) == 3:
                for i, j in zip(keys_to_match_per_concept[9:12], concept_matches):
                    match_pc.append((j / i) * 100)
            else:
                for i, j in zip(keys_to_match_per_concept[12:], concept_matches):
                    match_pc.append((j / i) * 100)

            for i in range(len(match_pc)):
                if 'keywords' in results.keys():
                    self.concept_scores.append(((results['keywords'][i] + match_pc[i]) / 200) * 100)

    def show_results1(self):
        print("Site:%f, Onset:%f, Character:%f, \n"
              "Radiation:%f, Associated symptoms:%f, Timing:%f, \n"
              "Exacerbating and relieving factors:%f, Severity:%f\n"
              % (self.concept_scores[0], self.concept_scores[1], self.concept_scores[2],
                 self.concept_scores[3], self.concept_scores[4], self.concept_scores[5],
                 self.concept_scores[6], self.concept_scores[7]))

    def show_results2(self):
        print("PH:%f, DH:%f, FH:%f, \n"
              % (self.concept_scores[8], self.concept_scores[9], self.concept_scores[10]))

    def compute_score(self):
        for i in range(len(self.concept_scores)):
            if self.concept_scores[i] > 0:
                self.score += 1
            else:
                if len(self.concept_scores) == 9:
                    self.excluded.append(self.SOCRATES[i])
                elif len(self.concept_scores) == 3:
                    self.excluded.append(self.ICE[i])
                else:
                    self.excluded.append(self.PH[i])
        return [self.score, self.excluded]

