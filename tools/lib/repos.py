
"""
Julie Zelenski, 2014-present

All-new (2014) Repo class that manages location/status/operations of repo for given student/assignmane
At its core, a Repo is pretty much only just a student+reponame pair, it knows where to look
on disk to get more info, and can dig in to get status, grade report, etc.
The "on demand" feature is done by waiting until an attribute is actually requested to
go ferret it out, but then caching it for repeated access.
"""

import datetime, glob, os
import course, gen, submits, ui, util
from common import *
from pairing import Pairing
from webreview import WebReview
from git import Git


class Repo(object):
    """ This is the Thick Repo object, defined by reponame+sunet -- path to repo will be constructed according to pattern"""
    ERROR, NONEXISTENT, UNTOUCHED, UNSUBMITTED, SUBMITTED, DIRTY, UNGRADED, GRADED, RELEASED, NSTATUS = range(10)
    STATUS_STR = ["ERROR", "nonexistent", "untouched", "unsubmitted", "submitted", "dirty", "ungraded", "graded", "released", "nstatus"]

    SUBMIT_LATEST = "tags/tools/submit/latest"

    @staticmethod
    def sunets_for_reponame(reponame):
        # harvests sunets from union of public/private
        return util.without_duplicates([os.path.basename(p) for p in glob.glob(Repo.private_repo_path(reponame, "*")) + glob.glob(Repo.public_repo_path(reponame, "*"))])

    @staticmethod
    def reponames_for_sunet(sunet):
        return util.without_duplicates([os.path.basename(os.path.dirname(p)) for p in glob.glob(Repo.private_repo_path("*", sunet)) + glob.glob(Repo.public_repo_path("*", sunet))])

    @staticmethod
    def repos_from_dir(reponame):
        return [Repo(reponame, s) for s in Repo.sunets_for_reponame(reponame)]

    @staticmethod
    def repos_for_sunet(sunet):
        return [Repo(r, sunet) for r in Repo.reponames_for_sunet(sunet)]

    @staticmethod
    def sunets_from_all_repos():
        all = [Repo.sunets_for_reponame(r) for r in course.assign_names()]
        return util.without_duplicates(util.flatten(all))

    @staticmethod
    def public_repo_path(reponame, sunet=""):
        return os.path.join(course.public_repo_path(), reponame, sunet)

    @staticmethod
    def private_repo_path(reponame, sunet=""):
        return os.path.join(gen.PRIVATE_DATA_PATH, "repos", reponame, sunet)

    @staticmethod
    def push_path(reponame, sunet):
        return Repo.public_repo_path(reponame, sunet)

    # take any number of keyword args to set as fields
    def __init__(self, reponame, sunet):
        self.reponame = reponame
        self.sunet = sunet

    def __str__(self):
        return self.sunet  # used when printing abbreviated list of sunets

    def __repr__(self):
        return "Repo:" + self.id

    def __getattr__(self, name):
        # if we get here, named attribute does not (yet) exist for this instance
        # lookup method for named attribute and use it to retrieve/compute instead
        # method to retrieve/compute will called _get_fieldname, will be called once
        # then return value cached for future use
        method_name = "_get_%s" % name
        if not hasattr(self, method_name):
            raise AttributeError("%s object has no attribute '%s', nor method '%s'." % (self.__class__.__name__, name, method_name))
        # if getter found, call it, set value will cache for future access, return it
        value = getattr(self, method_name)()
        setattr(self, name, value)
        return value

    def _get_id(self):
        return "%s/%s" % (self.reponame, self.sunet)

    def _get_path(self):
        return self.private_repo_path(self.reponame, self.sunet)

    def _get_sub(self):
        return submits.Submission.load(self.path, True)  # load will only read existing, no create if not there

    def _get_webreview(self):
        return WebReview.load(self.path)   # load will only read existing, no create if not there

    def _get_ta(self):
        if self.sub and self.sub.gradedby: return self.sub.gradedby  # once graded, grading TA takes precedence
        return Pairing.for_assign(self.reponame).ta_for_sunet(self.sunet)  # otherwise use pairing assignment

    def _get_tags(self):
        return Pairing.for_assign(self.reponame).tags_for_sunet(self.sunet)

    def pairings_match(self, to_include, to_exclude):
        """takes a list of terms and returns True if repo's pairings (ta or tags) match any term.
            Note that empty to_include includes all, empty to_exclude excludes none"""
        if not to_include and not to_exclude: return True  # empty criteria, don't even retrieve ta/tags
        mytags = [self.ta] + self.tags
        return (not to_include or any(t in to_include for t in mytags)) and (not to_exclude or not any(t in to_exclude for t in mytags))

    def _get_prettyname(self):
        info = course.assign_info(self.reponame)
        if not info: return self.reponame
        return info.name

    def _get_public_git(self):
        return Git(self.public_repo_path(self.reponame, self.sunet))

    def _get_private_git(self):
        # JDZ: fetch here ???
        return Git(self.path)

    def _get_status_string(self):
        return self.STATUS_STR[self.status]

    def _get_status(self):
        if not os.path.exists(self.public_git.path) and not os.path.exists(self.path): return self.NONEXISTENT
        assert os.path.exists(self.public_git.path) and os.path.exists(self.path), " *** Inconsistent public/private repo %s ***" % self.id
        if self.sub:
            if self.sub.released: return self.RELEASED
            if self.sub.gradedby: return self.GRADED
        if self.private_git.has_branch_named("grading"):
            if self.grading_branch_is_dirty(): return self.DIRTY
            return self.UNGRADED
        if self.has_submit_tag(): return self.SUBMITTED
        if self.public_is_touched(): return self.UNSUBMITTED
        return self.UNTOUCHED

    def _get_grading_head(self):
        return self.private_git.hash_for_rev("grading")

    def _get_submit_datetime(self):
        # Always use submit time from submit tag, even if grading a different revision
        return self.public_git.time_of_rev(self.SUBMIT_LATEST)

    def _get_partner(self):
        return self.private_git.read_partner()

    def is_stale(self):
        if self.sub.revision != self.grading_head:
            print ui.red("%s sub revision %s != %s grading head" % (self.id, self.sub.revision, self.grading_head))
            return True
        private_changes = self.local_git.has_uncommitted_changes()
        if private_changes:
            print ui.red("%s has changes gcache %s" % (self.id, self.sub.revision, self.grading_head))
            return True
        return False

    def rev_to_grade(self):
        p = os.path.join(self.path, "HASH_TO_GRADE")
        if os.path.exists(p):
            rev = util.read_file(p).strip()   # file contains the hash of the revision to grade (override)
        else:
            rev = self.SUBMIT_LATEST
        return rev

    def prep(self):
        assert self.status == self.SUBMITTED, "Can only prep if status == submitted, %s is %s" % (self.id, self.status_string)
        # fetch --tags to bring in all tags (even those that may not be on the master branch
        # this is relevant when they have submit/latest tag obscured by
        # later auto_push
        self.private_git.git_command("fetch --tags --force")
        self.private_git.reset_hard("origin/master")     # sync with public (master branch often used, but just in case)
        self.private_git.create_checkout_branch("grading")  # create grading branch
        self.private_git.reset_hard(self.rev_to_grade())  # force branch HEAD to correct revision

    def grading_branch_is_dirty(self):
        dirty = False
        if self.private_git.current_branch() != "grading": dirty = True
        public_submit = self.public_git.hash_for_rev(self.SUBMIT_LATEST)
        private_submit = self.private_git.hash_for_rev(self.SUBMIT_LATEST)
        if public_submit != private_submit: dirty = True
        if self.private_git.has_uncommitted_changes(): dirty = True
        to_grade = self.private_git.hash_for_rev(self.rev_to_grade())
        if self.grading_head != to_grade: dirty = True
        if gen.is_instructor() and dirty:
            print ui.red("\n %s DIRTY! (run repo_tool --reprep to investigate situation)" % self.id)
        return dirty

    def public_is_touched(self):
        return self.public_git.hash_for_rev("HEAD") != self.public_git.hash_for_rev("tags/tools/create")

    def dirty_from_resubmit(self):
        on_grading = self.private_git.current_branch() == "grading"
        public_submit = self.public_git.hash_for_rev(self.SUBMIT_LATEST)
        private_submit = self.private_git.hash_for_rev(self.SUBMIT_LATEST)
        resubmit = public_submit != private_submit
        clean = not self.private_git.has_uncommitted_changes()
        return on_grading and resubmit and clean

    def reprep(self):
        print
        assert self.status == self.DIRTY, "Can only re-prep if status == dirty, %s is %s" % (self.id, self.status_string)
        if self.dirty_from_resubmit():
            print "\n%s has newer submit. Will fetch tags and reset to submit/latest" % self.id
            self.private_git.git_command("fetch --tags --force")
            self.private_git.reset_hard(self.SUBMIT_LATEST)
        if self.grading_branch_is_dirty():
            ui.warn("full re-prep not yet implemented!")
            print ui.red("Sorry! Ask Julie to manually fix this repo")
            print "\t on grading branch?", self.private_git.current_branch() == "grading"
            print "\t public == private submit/latest?", self.public_git.hash_for_rev(self.SUBMIT_LATEST) == self.private_git.hash_for_rev(self.SUBMIT_LATEST)
            print "\t all changes committed?", not self.private_git.has_uncommitted_changes()
            print "\t grading head == %s?" % self.rev_to_grade(), self.grading_head == self.public_git.hash_for_rev(self.rev_to_grade()) 
            #    if uncommitted changes, must commit (to keep changes) or reset (to discard)
            # to move grading head, use reset hard


    def start_grading(self):
        if self.sub is not None:
            if self.sub.revision == self.grading_head:
                return self.sub
            else:
                print ui.faint("Discarding stale GCACHE for %s" % self.id)
        else:
            print ui.faint("Creating GCACHE for %s" % self.id)
        self.sub = submits.Submission(self.reponame, self.path, self.grading_head, self.submit_datetime)
        self.sub.commit_changes()  # writes iniitial GCACHE (empty)
        return self.sub

    def remove_submit_tag(self):
        util.system("find %s -type d -print0 | xargs -0 -n 1 -I FNAME fs sa FNAME %s all" % (self.public_git.path, gen.username()))
        self.public_git.git_command("tag -d tools/submit/latest")
        #ui.warn("remove submit tag (or any edits) to public won't work")
        # need a new strategy -- won't be able to delete tag on public
        # instead add a submit/superceded thing?

    def has_submit_tag(self):
        return self.public_git.hash_for_rev(self.SUBMIT_LATEST) is not None

    def remove_existing(self):
        util.force_remove_dir(self.public_git.path)
        util.force_remove_dir(self.private_git.path)

    def manual_submit_tag(self):
        util.system("find %s -type d -print0 | xargs -0 -n 1 -I FNAME fs sa FNAME %s all" % (self.public_git.path, gen.username()))
        hash = raw_input("\nEnter hash to tag:")
        if not hash: 
            print ui.red("Can enter HEAD to tag latest, otherwise specify hash, empty response will tag nothing")
        else:
            self.public_git.git_command("tag -f tools/submit/latest %s" % hash)

    def init_empty(self):
        assert not os.path.exists(self.public_git.path), "cannot init on top of existing repo %s" % self.id
        self.public_git.init_bare()
        self.public_git.clone(self.path)
        # bare repo is empty other than the .git subdir, add one file to appear less weird
        util.write_file("This directory contains a %s repo.\n" % gen.COURSE, os.path.join(self.public_git.path, "description"))
        self.private_git.commit_allow_empty("Init empty repo")
        self.private_git.push_to_origin()

    def commit_starter_and_tag(self, msg):
        self.private_git.add(".")
        self.private_git.commit_allow_empty(msg)
        self.private_git.tag("tools/create")
        self.private_git.push_to_origin()

    def grading_concerns(self):
        """look for irregularities (HEAD not at submit/latest, past grace period) to be confirmed by grade.
           return concerns if something seems out of whack"""
        concerns = ""
        bname = self.private_git.current_branch()
        assert bname == "grading", "starting to grade %s, but doesn't have grading branch checked out!" % self.id
        public_submit = self.private_git.hash_for_rev(self.SUBMIT_LATEST)
        to_grade = self.rev_to_grade()
        private_head = self.private_git.hash_for_rev("HEAD")
        if private_head != self.private_git.hash_for_rev(to_grade):
            concerns += "%s private grading HEAD revision != revision to grade\n" % self.id
        if self.sub.subdate and course.check_submit_lateness(self.reponame, self.sub.subdate) == course.TOO_LATE:
            concerns += "%s submission dated %s, this was after end of grace period\n" % (self.id, ui.nicedatetime(self.sub.subdate))
        return concerns if len(concerns) else None


# NOTES
# we (staff group) have only rla permissions to public repo
# this is to prevent us from any destructive operations on it
# only student has access to public
#
# the private repo is maintained as mirror of public
# (the sync operation is fetch/reset hard)
# prep/re-prep perform a sync
# dirty used for needs sync or wd of private is unclean
#
# tags are sync'ed, but should get tag reference on
# public to be sure of getting "truth" rather than
# any stale local state in private

