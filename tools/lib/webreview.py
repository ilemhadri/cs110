
"""
Michael Chang, 2013-present

WebReview class that encapsulates info about the grader review of a submission
Both the cgi-bin side and command-line tools use WebReview object to read/write
grader's scores/comments.
A grader review is stored as a pickle file named WEB_REVIEW
"""

import cPickle, glob, os
import course, ui, util
from common import *

class WebReview(object):
    MANIFEST_FILENAME = "WEB_REVIEW.ini"
    REVIEW_FILENAME = "WEB_REVIEW"

    def __init__(self, path_to_self, template_dir):
        """ Don't call this, call load() instead. """
        self.writeback_path = path_to_self
        path = os.path.join(template_dir, self.MANIFEST_FILENAME)
        asserts.manifest(os.path.exists(path), "%s does not exist" % path)
        config = util.read_config(path)
        f_patterns = config["main"]["files"]
        d_patterns = config["main"]["diff_files"] if "diff_files" in config["main"] else []
        g_patterns = config["main"]["grader_files"] if "grader_files" in config["main"] else []
        self.gather_files_to_review(f_patterns, d_patterns, g_patterns)
        self.comments = dict(((f, {}) for f in self.files))  # only allow comments on student-visible files
        self.overview = ""
        self.items = {}
        for name, fields in config.items():
            if name == "main": continue
            asserts.manifest("choices" in fields and isinstance(fields["choices"],list), "Webreview item %s has no/invalid list of choices '%s'" % (name, fields["choices"]))
            choices = [str(c) for c in fields["choices"]]  # ConfigParser may have converted entries to int, return to string form
            del fields["choices"]  # we will massage into another form, don't keep original

            # initialize item with default fields
            item = util.Struct(instructions_to_grader=None, optional=False, score="", displayed_score="")
            item.update(**fields)  # update fields read from manifest
            item.instructions_to_grader = " (%s)" % item.instructions_to_grader if item.instructions_to_grader else ""
            # if all choices are numbers, this is numeric item, label choices as "choice/fullcredit"
            item.numeric = all(util.is_int(n) for n in choices)
            if item.numeric and not hasattr(item, "fullcredit"):
                # if fullcredit not explicitly set in manifest, assign here to max value among choices
                item.fullcredit = max(int(c) for c in choices)
            item.labeled_choices = [(c, self.label_for_choice(item, c)) for c in choices]
            self.items[name] = item
        for (name, item) in sorted(self.items.items()):
            if hasattr(item, "fullcredit"):
                asserts.manifest(isinstance(item.fullcredit, int), "Webreview item %s has invalid fullcredit %s" % (name, item.fullcredit))
                asserts.manifest(item.numeric, "Webreview item %s cannot set fullcredit unless choices are numeric" % name)
            asserts.manifest(not item.optional or item.numeric, "Webreview item %s cannot be optional unless choices are numeric" % name)
            fields = set(item.__dict__.keys())
            deprecated = {"kind", "text", "grader_text", "denominator"} & fields
            asserts.manifest(len(deprecated) == 0, "Webreview item %s refers to deprecated fields %s" % (name, list(deprecated)))
            missing = {"description"} - fields
            asserts.manifest(len(missing) == 0, "Webreview item %s missing required fields %s" % (name, list(missing)))

    def label_for_choice(self, item, choice):
        if item.numeric:
            return "%s/%s" % (choice, item.fullcredit) if item.fullcredit != 0 else "%+d" % int(choice)
        else:
            return choice

    def set_score_for_name(self, name, score):
        item = self.items[name]  # item is Struct (e.g. alias/pointer), can modify in place
        item.score = str(score)
        item.displayed_score = self.label_for_choice(item, score) if item.score != "" else ""

    # point/bucket return list of items, sorted by name
    def point_items(self):
        return [item for (name, item) in sorted(self.items.items()) if item.numeric]

    def bucket_items(self):
        return [item for (name, item) in sorted(self.items.items()) if not item.numeric]

    def point_total(self):
        return sum(int(item.score) if item.score != "" else 0 for item in self.point_items())

    def bucket_total(self):
        return "|".join(item.score for item in self.bucket_items())

    def points_possible(self):
        return sum(item.fullcredit for item in self.point_items() if not item.optional)

    def has_points(self):
        return len(self.point_items()) != 0

    def has_buckets(self):
        return len(self.bucket_items()) != 0

    def is_complete(self):
        return self.overview and all(item.score is not "" or item.optional for item in self.items.values())

    def __getstate__(self):
        """overridden to remove transient/volatile variables from what is pickled"""
        state = dict(self.__dict__)  # copy our dict
        del state["writeback_path"]     # don't save path in pickle file, always re-set from where read
        return state

    def save(self):
        assert(self.writeback_path), "cannot save web review to empty writeback path"
        tmpfile = self.writeback_path + "~"
        with open(tmpfile, "w") as fp:
            cPickle.dump(self, fp)
        os.rename(tmpfile, self.writeback_path)  # atomic save, just in case

    def matched_files(self, repo_path, patterns):
        globbed = sum((glob.glob("%s/%s" % (repo_path, f)) for f in patterns), [])
        return util.without_duplicates((f[len(repo_path) + 1:] for f in globbed))

    def make_diff_files(self, repo_path, diff_patterns):
        # TODO: MC: Maybe should move this into git module?
        DIFF_OPTIONS = "--text --ignore-all-space tools/create"
        diffs = []
        for f in self.matched_files(repo_path, diff_patterns):
            output = util.system("git -C '%s' diff %s -- '%s'" % (repo_path, DIFF_OPTIONS, f))
            if output != "":
                fname = "%s.diff" % f
                util.write_file(output, "%s/%s" % (repo_path, fname))
                diffs.append(fname)
        return diffs

    def gather_files_to_review(self, file_patterns, diff_file_patterns, grader_file_patterns):
        if self.writeback_path is None:  # if this is unanchored use of template, use patterns as set in config for files
            self.files = file_patterns + ["%s.diff" % f for f in diff_file_patterns]
            self.grader_files = grader_file_patterns
        else:
            repo_path = os.path.dirname(self.writeback_path)
            self.files = self.matched_files(repo_path, file_patterns) + self.make_diff_files(repo_path, diff_file_patterns)
            self.grader_files = self.matched_files(repo_path, grader_file_patterns)

    @classmethod
    def create(cls, path, template_dir):
        wr = cls.load(path)  # load existing if found
        if not wr:           # otherwise, create from template
            wr = cls(os.path.join(path, cls.REVIEW_FILENAME), template_dir)
            wr.save()
        return wr

    @classmethod
    def load(cls, path):
        """Try read cached object from pickle file"""
        picklepath = os.path.join(path, cls.REVIEW_FILENAME)
        if os.access(picklepath, os.R_OK):
            with open(picklepath) as f:
                wr = cPickle.load(f)
            # unarchived web review needs path being read from, path not stored in pickle
            wr.writeback_path = picklepath
            return wr
        return None

    @classmethod
    def read_template(cls, template_dir):
        return cls(None, template_dir)

    @classmethod
    def grade_in_browser(cls, repo):
        print "Update review in browser at %s" % ui.blue(course.url_review(repo.reponame, repo.sunet))
        while True:
            try:
                response = raw_input("After finishing in browser, press return to continue: ")
                if response == "cli": return cls.grade_interactive(repo)
                wr = cls.load(repo.path)  # re-load contents (browser will have updated)
                if not wr: return False
                if wr.is_complete(): return True
                if not wr.overview:
                    print ui.red("Overview comment is empty. Please fix in browser.")
                else:
                    print ui.red("One or more required items is unscored! Please fix in browser.")
            except KeyboardInterrupt:  # ^C allows grader to defer dealing with this one now
                print " *** Grader canceled *** "
                return False

    @classmethod
    def grade_interactive(cls, repo):
        # JDZ: This is half-baked CLI to edit web review. Intended for me to grade assign0
        wr = cls.load(repo.path)  # don't need to reload as we are directly updating it
        try:
            for key, item in sorted(wr.items.items()):
                choices = [x[0] for x in item.labeled_choices]
                previous = item.score if item.score != "" else None
                score = ui.get_choice("Enter score for [%s]" % key, choices, default=previous)
                wr.set_score_for_name(key, score)
            if wr.overview: print "Previous overview comment: %s" % ui.blue(wr.overview)
            overview = None
            while not overview:
                overview = raw_input("Enter overview comment for student: ")
                if not overview and wr.overview: overview = wr.overview  # use previous if no entry
            wr.overview = overview
        except KeyboardInterrupt:  # ^C allows grader to defer dealing with this one now, no changes saved
            print " *** Grader canceled *** "
            return False
        wr.save()
        return True
