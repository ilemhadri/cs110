
"""
Julie Zelenski, 2011-present

Submission class that encapsulates info about a grade report.
A grade report consists of a dict of test names and results, along with
the submit information (revision, submission date, days late)
A grade report is stored as a pickle file named GCACHE
"""

import collections, cPickle, datetime, os
import course, gen, results, util


class Submission(object):
    """This object represents the grade report for a student's submission."""

    P_FILENAME = "GCACHE"
    VERSION = 2  # attempt as simple versioning system to not blunder through GCACHE changes

    def __init__(self, reponame, repo_path, head_rev, subdate):
        self.version = self.VERSION
        self.testresults = {}
        self.released = False
        self.gradedby = None
        self.reponame = reponame
        self.revision = head_rev
        self.subdate = subdate
        self.numlate = course.compute_late_days(reponame, self.subdate) if self.subdate else -1
        self.ontime_bonus = course.ontime_bonus(reponame)
        self.late_policy = course.late_policy(reponame)
        self.writeback_path = os.path.join(repo_path, self.P_FILENAME)

    def __getstate__(self):
        """overridden to remove transient/volatile variables from what is pickled"""
        state = dict(self.__dict__)  # copy our dict
        if "writeback_path" in state: del state["writeback_path"]  # don't save the path in pickle, always re-set from where read
        return state

    def mark_finished(self):
        '''upon completing last needed test, this is when submission recorded as finished with grading'''
        has_deferred_tests = any(r.deferred() for r in self.testresults.values())
        if not has_deferred_tests and self.gradedby is None:
            self.gradedby = gen.username()  # at finish grading, set grader
            self.finishtime = datetime.datetime.now()
            self.commit_changes()

    def set_released(self, val):
        if self.released != val:
            if not val:
                self.released = False
            elif self.gradedby:  # should only release repos that are finished grading
                self.released = True
            else:
                raise Exception("repo has incomplete grading, cannot release")
            self.commit_changes()

    def commit_changes(self):
        if not self.writeback_path: return
        # GCACHE is a symlink for a partnered assign7
        # it is error to be writing through to it and should never happen
        assert(not os.path.islink(self.writeback_path)), "Cannot write through linked GCACHE %s" % self.writeback_path
        tmpfile = self.writeback_path + "~"
        with open(tmpfile, "w") as fp:
            cPickle.dump(self, fp)
        os.rename(tmpfile, self.writeback_path)  # atomic save, just in case

    def cached_result_for(self, test):
        return self.testresults[test.name] if test.name in self.testresults else None

    def save_test_result(self, testname, result):
        if result:
            self.testresults[testname] = result
        elif testname in self.testresults:  # setting result to None removes test from results
            del self.testresults[testname]
        self.commit_changes()  # dump intermediate results after test run

    MANUAL_ADJUSTMENT = "Adjustment"

    def adjust_total(self, points, reason):
        if points == 0:
            result = None  # setting result to None will cancel any existing adjustment
        else:
            test = util.Struct(name=self.MANUAL_ADJUSTMENT, description="point total was manually adjusted", totalpts=0)
            result = results.Points(score=points, short=reason)
            result.set_test(test)
        self.save_test_result(self.MANUAL_ADJUSTMENT, result)

    def summary_string(self, verbose=False):
        result = "Points: %3d/%-3d" % self.points_tuple()
        if self.buckets(): result += " Review: %s" % self.buckets()
        if verbose: result += " Timeliness: %s" % self.late_or_bonus_string()
        return result

    def bonus_points(self):
        due = course.duedate_for(self.reponame)[0]
        if self.reponame == 'assign4':
            early_deadline = due - datetime.timedelta(days=1) + datetime.timedelta(hours=6)
            if self.subdate <= early_deadline:
                return int(round(self.points()*0.03))
        if self.numlate == 0:
            return int(round(self.points()*self.ontime_bonus))  # earned functionality * percent
        else:
            return 0

    def late_or_bonus_string(self):
        if self.numlate != 0: return "late"
        pts = self.bonus_points()
        return "on-time" + (" bonus +%d" % pts) if pts != 0 else ""

    def late_discount(self):
        if self.numlate == 0:
            pts = self.bonus_points()
            return "on-time" + ((", +%d early bonus will be added" % pts) if pts != 0 else "")
        # JDZ this is hard-coded quick fix for Jerry 110
        cap = 50
        if self.numlate == 1: cap = 90
        if self.numlate == 2: cap = 80
        return "%d day%s late, score will be capped to %d%%" % (self.numlate, "s" if self.numlate != 1 else "", cap)

    def grade_summary(self):
        d = collections.defaultdict(str)  # use empty string as val for any unknown key
        d["Functionality"] = self.points_string()
        d["Percentage"] = self.percentage()
        d["PercentageString"] = self.percentage_string()
        if self.buckets(): d["Review"] = self.buckets()
        d["Notes"] = self.late_or_bonus_string() if self.late_policy == "grace" else self.late_discount()
        return d

    def points(self):
        return self.points_tuple()[0]

    def points_string(self, verbose=False):
        return "%d/%d " % self.points_tuple() + (self.late_or_bonus_string() if verbose else "")

    def cap(self):
        if self.numlate == 0: return 100
        if self.numlate == 1: return 90
        if self.numlate == 2: return 70
        return 50

    def extra_percentage_points(self):
        return 0.0
    
    def percentage(self):
        return min(self.cap(), 100.0 * self.points() / self.points_tuple()[1]) + self.extra_percentage_points()

    def percentage_string(self):
        return "%.2f%%" % self.percentage()
    
    def buckets(self):
        return next((r.buckets for r in self.testresults.values() if r.scored_in_buckets()), None)

    def points_tuple(self):  # tuple is (earned, possible)
        return results.sum_points(self.testresults.values())

    def points_tuple_matching(self, pattern, exclude=None):
        return results.sum_points([self.testresults[name] for name in self.testresults if pattern in name and name != exclude])

    def test_keys(self):
        return [k for k in self.testresults.keys() if k != self.MANUAL_ADJUSTMENT]  # don't expose the special adjustment entry

    def remove_stale_tests(self, testnames):
        for n in testnames:
            del self.testresults[n]
        self.commit_changes()

    LAST_READ_TIME = 0

    @classmethod
    def load(cls, path, writeback=False):
        """Read cached object from pickle file, otherwise return None """
        picklepath = os.path.join(path, cls.P_FILENAME)
        if not os.access(picklepath, os.R_OK):
            return None  # if no GCACHE, return None, don't fake up empty placeholder
        with open(picklepath, "r") as fp:
            import time
            start = time.time()
            sub = cPickle.load(fp)  # will raise on error
            end = time.time()
            elapsed = end - start
            if elapsed > cls.LAST_READ_TIME:
                #print "GCACHE read %g (%s)" % (elapsed, gen.shortpath(path))
                cls.LAST_READ_TIME = elapsed

            assert(hasattr(sub, "version") and sub.version == cls.VERSION), "%s incompatible with this version of tools" % gen.shortpath(picklepath)
            # unarchived web review needs path being read from, path not stored in GCACHE/WEB_REVIEW
            for r in sub.testresults.values():  # manually update webreview result (yuck)
                if isinstance(r, results.ParseWebReview):
                    r.was_loaded_from_path(path)
            sub.writeback_path = picklepath if writeback else None
            return sub
