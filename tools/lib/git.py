"""
Julie Zelenski, 2016-present

Modules started to hold interfaces to git.
Master/tools repos switched to git 15-3
Student repos changing over 17-1
"""
import datetime, os, tempfile
import gen, ui, util

class Git(object):

    @staticmethod
    def command(path, args):
        """possible override for subprocess execution? The standard util joins
        stderr with stdout, which is usually fine, but if cmd spews harmless
        warnings to stderr that can be safely ignored and need to be filtered out. This tweaked
        version separates stdout from stderr and discards stderr, unless the return code was
        non-zero, in which case it reports stderr when raising exception"""
        #   process = subprocess.Popen(cmd, shell=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        #   out, err = process.communicate()
        #   assert(process.returncode == 0), "%s failed to execute (%s)" % (cmd, err)
        #   return out.strip()
        if path:
            # cmd = "git -C '%s' %s" % (path, args)  # git version on web is 1.7, doesn't support -C so workaround
            cmd = "(cd '%s'; git %s)" % (path, args)
        else:
            cmd = "git %s" % args
        out = util.system(cmd)   # non-zero return in system will raise, may want our own error handling wrapper, not sure
        # if gen.JZ_RUNNING: print ui.faint("\n\t%s\n\t=> %s" % (cmd, out))
        return out

    def git_command(self, args):
        """bottleneck all commands through this to set cwd to self.path"""
        return self.command(self.path, args)

    def __init__(self, path):
        self.path = path

    def is_valid(self):
        try:
            Git.command(None, "ls-remote %s" % self.path)    # no git -C as the path may not exist or be accessible
            return True
        except Exception:
            return False

    def hash_for_rev(self, rev):
        try:
            # rev-parse 3x faster than show -s --format=%%H %s
            return self.git_command("rev-parse %s" % rev)
        except:
            return None

    def time_of_rev(self, rev):
        # %ct is commit time, %at is author time, they are usually one and same, but not always
        # author time can be manually tweaked, and later rearrange of commits (rebase, etc.) will
        # retain author time and change commit, so seems like commit time is better option
        githash = self.hash_for_rev(rev)
        if not githash: return None
        timestamp = float(self.git_command("show -s %s --format=%%ct" % githash))
        return datetime.datetime.fromtimestamp(timestamp)

    def lock_path(self):
        return os.path.join(self.path, ".git", "index.lock")

    def is_locked(self):
        return os.path.exists(self.lock_path())

    def unlock(self):
        util.remove_files(self.lock_path())

    def tag(self, label):
        self.git_command("tag -f %s" % label)

    def delete_tag(self, label):
        try:
            self.git_command("tag -d %s" % label)
        except:
            pass  # fails if no such tag, ignore

    def commit(self, msg, options):
        author = gen.EMAIL_SENDER
        self.git_command("commit %s --author='%s' -m '%s'" % (options, author, msg))

    def commit_allow_empty(self, msg):
        # --allow-empty needed to force commit from submit when no new changes
        self.commit(msg, options="--allow-empty")

    def commit_if_dirty(self, msg):
        self.add_modified()
        if self.has_staged_changes(): self.commit(msg, options="")
        #if self.has_uncommitted_changes():
        #    # -a for all tracked files
        #    self.commit(msg, options="-a")

    def add(self, what):
        self.git_command("add %s" % what)

    def remove(self, what):
        self.git_command("rm --ignore-unmatch -f %s" % what)

    def add_modified(self):
        # names of modified (but not deleted) files
        files = self.git_command("diff --diff-filter=M --name-only").replace("\n", " ")
        # -- to ensure no filenames interpreted as options
        self.add("-- %s" % files)

    def init_bare(self):
        Git.command(None, "init --bare %s/.git" % self.path)    # no git -C as the path may not exist yet
        self.git_command("config core.logAllRefUpdates true")  # bare defaults to no reflog

    def clone(self, dstpath):
        self.git_command("clone . %s" % dstpath)
        return dstpath

    def make_tmp_clone(self):
        """clones to new path in /tmp, returns path to new clone"""
        return self.clone(tempfile.mkdtemp(dir="/tmp"))

    def reset_hard(self, rev):
        # not pull (which would send us through merge) 
        # instead grab latest and replace all tracked files in wd to match
        # I know reset --hard is scary, but is the right thing in this case
        self.git_command("reset --hard %s" % rev)

    def create_checkout_branch(self, name):
        self.git_command("checkout -b %s" % name)

    def has_branch_named(self, name):
        try:
            self.git_command("show-branch %s" % name)
            return True
        except Exception:
            return False

    def current_branch(self):
        return self.git_command("rev-parse --abbrev-ref HEAD")

    # this push used for submit and sanity
    def auto_push(self, dst_path):
        # --force (ok to discard commits if push is not fast-forward)
        # --tags to push tags
        # HEAD:master means push all commits from local HEAD onto remote master
        # (e.g. push current branch without thinking about its local name onto master)
        # specifiy dst_path, don't rely on "origin" (would be wrong for clone of clone)
        self.git_command("push --force --tags %s HEAD:master" % dst_path)

    def push_to_origin(self):
        # used on create to take private contents and push to public
        self.git_command("push --tags origin master")

    def has_staged_changes(self):
        # show files staged for commit, along with one-char status (Added, Modified, Deleted)
        out = self.git_command("diff --cached --name-status")
        if out == "": return None
        return out

    def has_uncommitted_changes(self):
        # --porcelain is short format (filename with M/DA), no funky colors
        # -uno means don't show untracked
        out = self.git_command("status --untracked-files=no --porcelain")
        if out == "": return None
        return out

    def file_is_largely_unchanged(self, filename, against=None):
        # diff file against initial revision and report if change seems small
        # diff options: -unified=0 0 lines of context (i.e. just changed lines), all files treated as text, ignore white
        if not against: against = self.hash_for_rev("tags/tools/create")
        diffs = self.git_command("diff --text --ignore-all-space --unified=0 --no-color %s -- %s" % (against, filename))
        # filter diff output to only added/changed lines
        new_lines = [line for line in diffs.split('\n') if line.startswith('+') and not line.startswith('+++')]
        new_text = ''.join(new_lines)
        return len(new_text) < 200 and len(new_lines) < 3  # require at least 3 added lines or 200 chars of text

    def read_metadata(self):
        manifest = os.path.join(self.path, ".metadata", "repo.ini")
        config = util.read_config(manifest)
        return util.Struct(**config["main"])

    def read_quarter(self):
        try:
            return self.read_metadata().quarter
        except:
            return None

    def read_reponame(self):
        try:
            return self.read_metadata().reponame
        except:
            return None

    def partner_path(self):
        return os.path.join(self.path,".metadata", "partner")

    def write_partner(self, partner):
        path = self.partner_path()
        if partner:
            util.write_file(partner, path)
            self.add(path)
        else:
            self.remove(path)

    def read_partner(self):
        return util.read_file(self.partner_path())

    def tag_submit(self, timestr, isforced):
        if isforced:
            self.tag("tools/submit/%s_forced" % timestr)
        else:
            self.tag("tools/submit/%s" % timestr)
        self.tag("tools/submit/latest")
