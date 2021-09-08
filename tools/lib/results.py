
"""
Julie Zelenski, 2011-present

The results module has the class hierarchy for different kinds of test results including
various ways of displaying them (formatting for dryrun, summary report, sanity check,
student grade report, etc. These are stored in the GCACHE pickle, so be careful about changes
that would introduce incompatibility.
"""

import operator, random
import scoring, testing, ui, util
from webreview import WebReview

class Result(object):
    onechar = ' '; did_pass = False; detail = ''
    score = 0
    test = None  # this struct will store essential fields copied from the Test object

    def __init__(self, **kwds):
        """when calling ctor can set any fields of Result object using syntax ivar=value"""
        self.__dict__.update(**kwds)

    def passed(self):
        return self.did_pass

    def deferred(self):
        return False

    def set_test(self, test):
        # save essential fields from Test object that produced this result, used later for reporting
        self.test = util.Struct(name=test.name, description=test.description, totalpts=test.totalpts)

    def scored_in_points(self):
        return isinstance(self.score, int)

    def scored_in_buckets(self):
        return False

    def score_string(self):
        if not self.scored_in_points():  # if score isn't a number at all
            return str(self.score)
        elif self.test and self.test.totalpts:  # has non-zero denominator
            return "%d/%d" % (self.score, self.test.totalpts)
        else:
            return "%+d" % (self.score)

    def summary_string(self):
        return self.short % self.__dict__  # performs named format substitution, enables use of placeholders in short

    def detail_string(self):
        return ui.convert_nonascii(ui.stripcolors(self.detail)) if self.detail else ''

    def string_for_context(self, context):
        if context == testing.FOR_SANITY:
            return self.string_for_sanity()
        elif context in [testing.FOR_AUTOGRADER, testing.FOR_RUNTESTS]:
            return "Result:  " + self.string_for_grader()
        elif context == testing.FOR_DRYRUN:
            return self.string_for_dryrun()
        else:
            return None

    def string_for_grader(self):
        str = "%s %s" % (self.score_string(), self.summary_string())
        if not self.did_pass: str = ui.red(str)
        return str

    def string_for_sanity(self):
        words = [ui.red("NOT OK"), ui.green("OK")]
        addl = ('\n' + self.detail) if self.detail else ''
        return "%s:  %s%s" % (words[self.did_pass], self.summary_string(), addl)

    def string_for_dryrun(self):
        return self.summary_string()

    def points_tuple(self):
        if self.scored_in_points():
            return (self.score, self.test.totalpts)
        else:
            return (0, 0)

    def __str__(self):
        return self.score_string() + (" (%s)" % self.__class__.__name__ if not self.passed() else "")

    def __ne__(self, other):
        # I'm not totally sure when this is being used
        return not other or (self.string_for_grader() != other.string_for_grader())

    def __repr__(self):
        return "<%s>" % self.__class__.__name__

    def __cmp__(self, other):
        # this is being used to order different results when sorting the dryrun table
        return cmp(self.__class__.__name__, other.__class__.__name__)


class Correct(Result):
    onechar = ' '; short = "Correct"; did_pass = True
    matched_output = ''  # don't record in usual case, but set and used for sanity

    def string_for_sanity(self):
        str = Result.string_for_sanity(self)
        if self.matched_output: str += "\nMatched output: %s" % ui.faint(prefix(ui.abbreviate(self.matched_output, maxlines=5)))
        return str

class Incorrect(Result):
    onechar = 'X'; short = "Submission behavior was incorrect"

class MismatchOutput(Result):
    onechar = 'o'; short = "Submission output does not match sample"
    output = None; correct_output = None

    def string_for_sanity(self):
        # when reporting output discrepancy for sanity, label as Mismatch, instead of definitive Not Ok
        return "%s:  %s\n%s" % (ui.red("MISMATCH"), self.summary_string(), print_mismatch_for_sanity(self.output, self.correct_output))

    def string_for_dryrun(self):
        output = self.output if self.output else "<empty>"
        diff = scoring.diff_ignoring_white_old(self.correct_output, output)
        picked = "\n".join(util.grep_text("^>", diff))
        return ui.abbreviate(picked or diff, maxlines=6)

class Points(Result):
    onechar = ' '; short = ''

    def set_test(self, test):
        Result.set_test(self, test)
        self.did_pass = self.score >= self.test.totalpts
        if not self.did_pass: self.onechar = '<'  # use < for under full-credit

class TimedOut(Result):
    onechar = 't'; short = "Waited %(limit)s seconds, program did not complete"

    def summary_string(self):
        summary = self.short
        if hasattr(self, "solntime") and self.solntime: summary += " (soln completes in under %(solntime)s seconds)"
        if hasattr(self, "errmsg") and self.errmsg: summary += " (error logged: %(errmsg)s)"
        return summary % self.__dict__

class SignalRaised(Result):
    onechar = '*'; short = "Program terminated due to signal %(signal_string)s"

class Inconclusive(Result):
    onechar = '?'; short = "Unable to judge due to buggy/incomplete execution"

    def string_for_dryrun(self):
        return ui.abbreviate(self.detail, maxlines=3) if self.detail is not None else self.summary_string()

class MemBoth(Result):
    onechar = 'b'; short = "Valgrind report shows memory errors and leaks"

class MemLeak(Result):
    onechar = 'l'; short = "Valgrind report shows leaks but no memory errors"

class MemError(Result):
    onechar = 'e'; short = "Valgrind report shows memory errors but no leaks"

class TooMuch(Result):
    onechar = '>'; short = "Resource use beyond limit"

class BuildIssue(Result):
    onechar = 'w'; short = "Warnings produced during build"; is_error = False

    def __init__(self, **kwds):
        super(BuildIssue, self).__init__(**kwds)
        if self.is_error:
            self.onechar = '#'
            self.short = "Build failed due to error"

    def string_for_dryrun(self):
        return ui.abbreviate(self.detail, maxlines=3) if self.detail is not None else self.summary_string()

class NoExecute(Result):
    onechar = '#'; short = "Did not execute %(msg)s"

class ParseWebReview(Result):
    onechar = ' '; did_pass = True; short = "See Review tab for details"
    """This result is tied to what is in WEB_REVIEW. It doesn't store the score to avoid
     becoming stale, instead always parses from WEB_REVIEW.  When you init this results,
     pass additional field path=submission path, has_points=bool, has_buckets=bool"""

    # TODO JDZ retrieve everything fresh from wr -- don't store anything

    has_points = False; has_buckets = False

    def scored_in_points(self):
        return self.has_points

    def scored_in_buckets(self):
        return self.has_buckets

    def __getattribute__(self, name):
        if name == "score" or name == "buckets":
            # TODO: MC: Store the Repo rather than the path?
            wr = WebReview.load(self.path)
            if not wr: return None
            if name == "score":
                return wr.point_total()
            if name == "buckets":
                return wr.bucket_total()
        else:
            return object.__getattribute__(self, name)

    def __getstate__(self):
        """overridden to remove transient/volatile variables from what is pickled"""
        state = dict(self.__dict__)  # copy our dict
        if "path" in state: del state["path"]  # don't save the path in pickle, always re-set from where read?
        return state

    def was_loaded_from_path(self, path):  # unpleasant hack, called from submit after loading GCACHE
        self.path = path

    def string_for_grader(self):
        wr = WebReview.load(self.path)
        if not wr: return "Grader review not available"
        ptotal = "%s/%s " % (wr.point_total(), wr.points_possible()) if self.has_points else ""
        btotal = wr.bucket_total() if self.has_buckets else ""
        return "%s%s Overview comment: %s" % (ptotal, btotal, wr.overview)

    def detail_string(self):
        # TODO JDZ not sure where this might show up, this helps dumpgrade -v not make special case
        # shows up in dink-down on functionalty page
        wr = WebReview.load(self.path)
        if not wr: return "Grader review not available"
        return wr.overview

    def deferred(self):
        wr = WebReview.load(self.path)
        return not wr or not wr.is_complete()

class Deferred(Result):
    onechar = 'D'; short = "Deferred"; score = "---"

    def deferred(self):
        return True

def summarize_mismatch(output, correct, detail=None):
    """ This tries to produce a useful report on what was wrong for student. Just dumping
    both outputs can be overwhelming, but entire diff can be hard to read. So tries to
    come up with summary for given situation.  Prefers printing both outputs (abbreviated)
    if mismatch is apparent from that context.  Otherwise, uses abbreviated diff"""
    if not detail:
        abbr_output = ui.abbreviate(output.strip(), maxlines=50)  # JDZ need a better policy than this!!
        abbr_correct = ui.abbreviate(correct.strip(), maxlines=50)
        newline = ' ' if (util.is_single_line(abbr_output) and util.is_single_line(abbr_correct)) else '\n'
        if not scoring.match_ok(abbr_output, abbr_correct):  # if prefix shows mismatch, print both
            return "Correct output:    %c%s%c\nSubmission output: %c%s\n" % (newline, abbr_correct, newline, newline, ui.blue(abbr_output))
    # otherwise, error is deeper, use the abbreviated diff instead
    # diffed = ui.abbreviate(scoring.diff_ignoring_white(correct, output), maxlines = 15)
    diffed = scoring.diff_ignoring_white_old(correct, output)
    diffed = ui.abbreviate(diffed, maxlines=50, maxlen=1000)
    return "Diff of correct output and submission output: \n%s\n" % ui.blue(diffed)

def random_cheer(seedstr=None):
    cheers = ["Excellent!", "Good job!", "Good on ya!", "Sweet!", "Bien hecho!", "Way to go!", "Super!", "Awesome!", "Great!", "Perfect!", "Nice work!", "You rock!", "Love it!", "Right on!", "No complaints here!", "Que bien!", "Buen trabajo!", "Bravo!", "Fantastico!", "Perfecto!", "Lo hiciste!", "Muy bien!", "Jolly good!", "Congratulations!", "Nice going!", "Terrific!", "Keep it up!", "You did it!"]
    if seedstr:
        return cheers[abs(hash(seedstr)) % len(cheers)]
    else:
        return random.choice(cheers)

def sum_points(results):
    """returns tuple of (earned, possible) points"""
    pairs = [r.points_tuple() for r in results]
    return tuple(reduce(lambda x,y: map(operator.add, x, y), pairs, (0, 0)))

def prefix(str):
    return str if util.is_single_line(str) else '\n' + str

def print_mismatch_for_sanity(output, soln_output):
    # MC: Hack for UTF-8. Is there a good way to know which non-ASCII are bad? Maybe cat -A helps?
    return "Sample output:  %s \nYour output:    %s" % (ui.normal(prefix(soln_output)), ui.blue(prefix(ui.convert_control_chars(output))))
