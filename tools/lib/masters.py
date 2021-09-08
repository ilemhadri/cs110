
"""
Julie Zelenski, 2015-present

Class to define handling for master repo, has default behavior for verify, clone, install.
Master repo directory can have master.py file that defines CustomMaster subclass to
overrides/extends any of those behaviors as desired.
"""

import ConfigParser, imp, os, util
import course, gen, ui, uid
from git import Git

class Master(object):

    # subclasses can set values of these variables to change these behaviors
    make_on_verify = True

    def __init__(self, path, reponame=None):
        """if reponame not explicitly set (typical case), will use last path component"""
        self.path = path.rstrip('/')
        self.reponame = os.path.basename(self.path) if not reponame else reponame

    def path_for(self, component):
        """returns path to component such as "starter", "docs", etc."""
        full_path = os.path.join(self.path, component)
        for dirname in ["/docs", "/samples", "/grade", "/starter"]:
            if dirname in full_path:
                dirname_with_suffix = dirname + self.suffix()  # check for alternate with suffix first
                path_with_suffix = full_path.replace(dirname, dirname_with_suffix)
                if os.path.exists(path_with_suffix): return path_with_suffix
        if os.path.exists(full_path): return full_path
        return full_path   # previously return None rather than a path to non-existent file/dir but changed to return path in case needed

    def suffix(self):
        """if reponame is assignN returns N, for other repos returns reponame unabbreviated"""
        num = util.match_regex("^assign(\d+)$", self.reponame)
        return num if num is not None else self.reponame

    def is_assign(self):
        return self.reponame.startswith("assign") or self.reponame in course.assign_names()

    def is_lab(self):
        return self.reponame.startswith("lab")

    def verify_starter(self):
        """Check starter and verify all in order, ready for cloning"""
        starter_path = self.path_for("starter")
        if os.path.exists(os.path.join(starter_path, ".hgignore")) or not os.path.exists(os.path.join(starter_path, ".gitignore")):
            ui.exit_done("Starter repo has no .gitignore file and/or has .hgignore file, fix now!")
        if self.make_on_verify and os.path.exists(os.path.join(starter_path,"Makefile")):
            util.system("cd %s && make clean" % starter_path)
            try:
                util.system("cd %s && make" % starter_path)
            except Exception as ex:
                print ui.red(str(ex))
                if not ui.get_yes_or_no("Build failed. Continue create anyway?"):
                    ui.exit_done("Fix build failure in %s starter!" % self.reponame)
            util.system("cd %s && make clean" % starter_path)

        # force show ignored because starter .gitignore may otherwise allow some junk files to be hanging around
        changes = Git.command(self.path, "status -s --ignored %s" % "starter")
        if changes:
            # cloning starter files with uncommitted changes is never going to be the right thing
            print ui.red("%s contains uncommitted changes:\n%s" % (gen.shortpath(starter_path), changes))
            ui.exit_done("Creating repos from a dirty starter is almost certainly a mistake! Stop and investigate.")
        return True

    def verify_master(self):
        """Check master and verify all in order, ready for cloning"""
        if self.make_on_verify and os.path.exists(os.path.join(self.path,"Makefile")):
                util.system("cd %s && make" % self.path)
        # untracked in master is not a big deal
        changes = Git.command(self.path, "status --short --untracked-files=no")
        if changes:
            # if master has uncommitted changes (but not starter), plausibly ok to make student clone
            print ui.red("%s contains uncommitted changes:\n%s" % (gen.shortpath(self.path), changes))
            print ui.red("Creating repos from a dirty master is plausibly harmless, but much better to stop here, verify state & commit.")
            ui.confirm_or_exit("Continue create anyway?")
        return True

    def add_files(self, dst_repo, starter):
        # -L deep copy sym links (pr preserve/recursive)
        # copy files from starter, but specifically ignore samples if already linked into starter
        util.system("cp -L -pr `find %s -mindepth 1 -maxdepth 1 -not -name samples` %s" % (starter, dst_repo.path))
        # make symlinks for samples/tools
        samples = self.path_for("samples")
        if os.path.exists(samples):  # make symlink to samples/assign in student repo
            os.symlink(os.path.join(gen.COURSE_PATH, "samples", self.reponame), os.path.join(dst_repo.path, "samples"))
        which_tools = []
        if course.assign_info(self.reponame) is not None:
            which_tools.append("submit")
            which_tools.append("fsr")
        if os.path.exists(os.path.join(samples, "SANITY.ini")):
            which_tools.append("sanitycheck")
        if which_tools:
            local_tools = os.path.join(dst_repo.path, "tools")
            os.makedirs(local_tools)
            for t in which_tools:
                os.symlink(os.path.join(gen.COURSE_PATH, "tools", t), os.path.join(local_tools, t))
        # create metadata folder with repo config
        mdpath = os.path.join(dst_repo.path, ".metadata", "repo.ini")
        config = ConfigParser.SafeConfigParser()
        config.add_section("main")
        info = {"course":gen.COURSE, "quarter":gen.QUARTER, "reponame":self.reponame, "sunet":dst_repo.sunet}
        for (key,val) in sorted(info.items()):
            config.set("main", key,val)
        os.makedirs(os.path.dirname(mdpath))
        with open(mdpath, "wb") as f:
            config.write(f)

    def create_student_repo(self, dst_repo, overwrite=False):
        """Init new repo for dst, copy/add/commit starter files"""
        if overwrite: dst_repo.remove_existing()
        dst_repo.init_empty()
        self.add_files(dst_repo, self.path_for("starter"))
        msg = "Created starter %s %s %s" % (gen.QUARTER, dst_repo.reponame, dst_repo.sunet)
        dst_repo.commit_starter_and_tag(msg)
        self.set_student_permissions(dst_repo)

    def set_student_permissions(self, dst_repo):
        #safety = [("mvaska","all"), ("service.cs-edu", "all")]  # JDZ FIXME This is not supposed to be the safety, but is for now
        safety = [("service.cs-edu", "all")]
        other_none = [("system:authuser","none"), ("system:anyuser","none")]
        staff_restricted = [(course.staff_afs_group(), "rla")]
        sunet_write = [(dst_repo.sunet,"rlidwk")]
        sunet_read = [(dst_repo.sunet,"rl")]
        other_read = [("system:anyuser","rl")]
        perms = lambda d: ' '.join("%s %s" % pair for pair in d)

        if not uid.is_valid_username(dst_repo.sunet):  # making for guest/shared
            if dst_repo.sunet not in ["guest", "shared"]:
                print "\tNOTE: %s has shared permissions (%s not valid username)" % (dst_repo.id, dst_repo.sunet)
            git_level = safety + other_read + staff_restricted
            top_level = safety + other_read
        else:
            git_level = safety + sunet_write + other_none + staff_restricted
            top_level = safety + sunet_read + other_none

        # apply permissions recursively using find/xargs to walk, since fsr doesn't propagage errors/exitcode :-(
        util.system("find %s -type d -print0 | xargs -0 -n 1 -I FNAME fs sa FNAME %s" % (os.path.join(dst_repo.public_git.path, ".git"), perms(git_level)))
        util.system("fs sa %s %s" % (dst_repo.public_git.path, perms(top_level)))

    def install(self):
        """Install samples/sanity, called after making student clones"""
        samples = self.path_for("samples")
        if os.path.exists(samples):
            dst = os.path.join(gen.COURSE_PATH, "samples", self.reponame)
            # -u only update if newer, -L deep copy sym links (pr preserve/recursive)
            util.system("mkdir -p %s && cp -u -L -pr %s/* %s" % (dst, samples, dst))
        return True

    def samples_need_update(self):
        samples = self.path_for("samples")
        if os.path.exists(samples):
            dst = os.path.join(gen.COURSE_PATH, "samples", self.reponame)
            return util.system_quiet("diff -r %s %s" % (samples, dst)) is not None
        return False

    def publish_docs(self):
        """this is where the handoff to doc_tool ought to go, but I was being lazy and letting repo_tool
        call it because it can import doc_tool from staff/bin dir"""
        if self.is_lab():
            dst = os.path.join(gen.PRIVATE_DATA_PATH, "lab_questions")
            quest = os.path.join(self.path_for("docs"), "_questions")
            util.system("mkdir -p %s && cp -u -p %s %s/%s" % (dst, quest, dst, self.reponame))

    def docs_need_update(self):
        if self.is_lab():
            dst = os.path.join(gen.PRIVATE_DATA_PATH, "lab_questions", self.reponame)
            quest = os.path.join(self.path_for("docs"), "_questions")
            if util.system_quiet("diff -r %s %s" % (quest, dst)) is not None: return True
        return True  # this needs to talk with doc_tool

    @classmethod
    def master_exists(cls, reponame):
        return os.path.exists(course.master_repo_path(reponame))

    @classmethod
    def master_for(cls, reponame):
        """Factory method to use as client. Returns Master object if path for master reponame exists, else returns None.
        Can override by supplying master.py file in master with subclass CustomMaster"""
        master_path = course.master_repo_path(reponame)
        custom_path = os.path.join(master_path, "master.py")
        if not os.path.exists(custom_path): return Master(master_path)
        module = imp.load_source("%s_custom" % reponame, custom_path)  # load as assignN_custom
        return getattr(module, "CustomMaster")(master_path)
