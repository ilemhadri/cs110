import csv, glob, os, sqlite3, math, sys, re

import gen, course, ui
from repos import Repo
from surveys import init_tables as init_survey_tables, get_surveys

def average(l):
    return sum(l) * 1.0 / len(l)

class Gradebook(object):
    def __init__(self, sunet):
        self.GRADES_PATH = gen.PRIVATE_DATA_PATH + "/grades"
        self.sunet = sunet
        self.sqlite_conn = sqlite3.connect(
                os.path.join(gen.PRIVATE_DATA_PATH, 'survey_responses.sqlite'))
        init_survey_tables(self.sqlite_conn)

    def assign_is_released(self, name):
        path = "%s/nosubmit_%s" % (self.GRADES_PATH, name)
        return os.access(path, os.R_OK)

    def csv_find(self, fname, whole=False):
        with open(fname, "r") as f:
            csvobj = csv.reader(f)
            for row in csvobj:
                if row[0] == self.sunet: return row[1] if not whole else row[1:]
        return None

    def get_cap(self, repo):
        days_late = repo.sub.numlate
        if days_late == 0:
            return sys.maxint
        elif days_late == 1:
            return 90
        elif days_late == 2:
            return 80
        else:
            return 50

    def get_final_assignment_func_score(self, repo, survey_bonus_points):
        points_earned, points_possible = repo.sub.points_tuple()
        bonus_points = repo.sub.bonus_points()
        score = 100.0 * (points_earned + bonus_points + survey_bonus_points) / points_possible
        return min(score, self.get_cap(repo))

    def get_style_grade(self, repo, style_to_score):
        if repo.sub.buckets():
            style_grades = [style_to_score[bucket] for bucket in repo.sub.buckets().split('|')]
            score = average(style_grades) * 100
        else:
            # e.g. MapReduce has no style grading
            score = 100
        return min(score, self.get_cap(repo))

    def get_assignments(self, survey_bonuses, style_to_score):
        result = []
        for i, assign in enumerate(course.assign_names()):
            repo = Repo(assign, self.sunet)
            if (repo.status == Repo.RELEASED):
                functionality = self.get_final_assignment_func_score(repo, survey_bonuses[assign])
                style = self.get_style_grade(repo, style_to_score)
                total_score = (5 * functionality + 1 * style) / 6.0
                result.append((assign, repo.prettyname, ui.nicedatetime(repo.sub.subdate),
                    repo.sub.grade_summary(), functionality, style, total_score))
            elif repo.status >= Repo.SUBMITTED:
                result.append((assign, repo.prettyname, ui.nicedatetime(repo.submit_datetime), None, None, None, None))
            elif self.assign_is_released(assign):
                result.append((assign, repo.prettyname, "Not submitted", None, None, None, None))
        return result

    def get_from_csv(self, type, whole=False):
        if type == "exam":
            files = sum((sorted(glob.glob("%s/%s.csv" % (self.GRADES_PATH, name))) for name in ("assessment?", "assessment-assignment*")), [])
            files = [f for f in files if os.access(f, os.R_OK)]
        elif type == "overall":
            files = sorted(glob.glob("%s/overall.csv" % self.GRADES_PATH))
        else: files = sorted(glob.glob("%s/%s*.csv" % (self.GRADES_PATH, type)))

        result = []
        for fname in files:
            name = os.path.splitext(os.path.basename(fname))[0].capitalize()
            score = self.csv_find(fname, whole=whole)
            result.append((name, score))
        return result

    def score_to_float(self, string):
        try:
            return int(string)
        except ValueError:
            return float(string.split('/')[0]) / float(string.split('/')[1])

    def concept_check_grade(self, concept_checks):
        grades = sorted([(self.score_to_float(score) if score else 0) for name, score in concept_checks])
        highest = grades[3:]
        return average(highest) * 100

    def curve_assessment_score(self, score_str):
        return math.sqrt(self.score_to_float(score_str)) * 100

    def get_total_grade(self, concept_check_grade, assign_grade, participation_grade, assessment_grade):
        return 0.1 * concept_check_grade + 0.6 * assign_grade + 0.1 * participation_grade + 0.2 * assessment_grade

    def extractNumber(self, string):
        return int(re.search(r'(\d+)', string).group(1))

    def get_overall_assignment_grade(self, assignments):
        min_grade = min(tup[-1] if tup[-1] else 0 for tup in assignments)
        if min_grade < 47.5:
            return min_grade
        return average([tup[-1] if tup[-1] else 0 for tup in assignments])

    def get_all_grades(self):
        grades = dict()

        grades["surveys"] = get_surveys(self.sqlite_conn, self.sunet)
        survey_map = { name: completed for (name, completed) in grades['surveys'] }
        assignments_to_surveys = {
            'assign1': ['Week 1'],
            'assign2': ['Week 2', 'Week 3'],
            'assign3': ['Week 4'],
            'assign4': ['Week 5'],
            'assign5': ['Week 6', 'Week 7'],
            'assign6': ['Week 8'] if Repo('assign7', self.sunet).status == Repo.RELEASED else ['Week 8', 'Final survey'],
            'assign7': ['Final survey'] if Repo('assign7', self.sunet).status == Repo.RELEASED else [],
        }
        survey_bonuses = {
            assign: sum(2 for survey in assignments_to_surveys[assign] if survey_map[survey])
            for assign in course.assign_names()
        }

        style_to_score = {
            'exceptional': 1.05,
            'solid': 1,
            'minor-problems': 0.8,
            'major-problems': 0.6,
            'nothing-written': 0,
            'great': 1,
            'minor-issues': 0.9,
            'major-issue': 0.75,
            'multiple-major-issues': 0.6,
            '0': 0,
        }

        grades["assignments"] = self.get_assignments(survey_bonuses, style_to_score)
        grades["labs"] = self.get_from_csv("lab")
        grades["participation_grade"] = self.get_from_csv("participation")[0][1]
        grades["exams"] = [(name, score, self.curve_assessment_score(score) if score else 0)
                for name, score in self.get_from_csv("exam")]
        grades["concept_checks"] = sorted(self.get_from_csv("concept_check_"), key=lambda pair: int(pair[0].split('_')[-1]))
        grades["concept_check_grade"] = self.concept_check_grade(grades["concept_checks"])

        # If submitted, the last assignment can be used to replace the lowest
        # assignment or assessment grade, whichever would lead to an improved
        # score
        top_assignments = sorted(grades['assignments'], key=lambda tup: (tup[-1] if tup[-1] else 0))[1:]
        if grades['assignments'][-1][-1]:
            boosted_exam_scores = sorted(tup[-1] for tup in grades['exams'])[1:] + [grades['assignments'][-1][-1]]
        else:
            boosted_exam_scores = [tup[-1] for tup in grades['exams']]
        grade_replacing_assignment = self.get_total_grade(grades['concept_check_grade'],
                self.get_overall_assignment_grade(top_assignments),
                self.extractNumber(grades['participation_grade'] if grades['participation_grade'] else '0'),
                average([tup[-1] for tup in grades['exams']]))
        grade_replacing_exam = self.get_total_grade(grades['concept_check_grade'],
                self.get_overall_assignment_grade(grades['assignments']),
                self.extractNumber(grades['participation_grade'] if grades['participation_grade'] else '0'),
                average(boosted_exam_scores))
        
        if grade_replacing_assignment > grade_replacing_exam:
            grades['assign7_context'] = 'used to replace lowest assignment'
            grades['overall_assignment_grade'] = self.get_overall_assignment_grade(top_assignments)
            grades['overall_exam_grade'] = average([tup[-1] for tup in grades['exams']])
            grades['final_grade'] = grade_replacing_assignment
        else:
            grades['assign7_context'] = 'used to replace lowest self-assessment'
            grades['overall_assignment_grade'] = self.get_overall_assignment_grade(grades['assignments'])
            grades['overall_exam_grade'] = average(boosted_exam_scores)
            grades['final_grade'] = grade_replacing_exam

        return grades

# vim: ts=4 sw=4 et


