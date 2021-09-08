
"""
Julie Zelenski, 2009-present
Ryan Noon, original design

The testing module has the logic for different kinds of tests and their execution
 -- Contains code for subprocess execution with timeout and I/O capture
 -- Parses manifest file to create list of applicable test per assignment
 -- Each Test is represented by instance within the hierarchy:
     The BaseTest class is the abstract superclass
     Various subclasses (DiffOutput, Valgrind, CodeReview,etc ) differ in
     how they are executed and/or scored (see scoring module)
"""

import copy, commands, inspect, math, os, pty, re, resource, signal, subprocess, sys, tempfile, time, traceback
import gen, results, scoring, ui, util
from common import *
from webreview import WebReview

# Constants to identify context under which test is running
FOR_SANITY, FOR_DRYRUN, FOR_RUNTESTS, FOR_PREGRADE, FOR_AUTOGRADER, FOR_TESTSUITE = range(6)

NO_EXEC_CODES = [125, 126, 127]  # 125 timeout cannot run, 126 bash no x permission, 127 bash command not found
TIMED_OUT_CODE = 124    # 124 status from timeout when period expires on monitored program
VALGRIND_ERROR_CODE = 88

# used for errors during execute_command
class TestExecuteError(Exception):
    pass

# if it was solution that failed, use this class instead
class SolutionError(Exception):
    pass

# set LIBC_FATAL_STDERR_=1 would cause glibc abort message to go to stderr instead of tty
# using pristine environment is appealing but then doesn't model what students will
# experience when running commands at shell, so didn't do this after all
#DEFAULT_ENV = {"SHELL":"/bin/bash", "PATH":"/usr/local/bin:/usr/bin:/bin", "LIBC_FATAL_STDERR_":"1"}

# new version of execute_command seems largely working at this point (March 2017)
# Has some advantages (e.g. core cmd exitcode more precise, leverage timeout, separate bash errors from program errors)
# and code somewhat less goopy (no more CRLF, bash scrape, etc).
# However, it has subtle dependencies (e.g. use of redirect to avoid bash exec-overlay)
# that may come back to haunt us later
def execute_command(wd, command, timeout=None, env_overrides={}, logged=False, solnlen=-1):
    """Run the specific command in directory wd.  Timeout specifies seconds to
    wait for command to finish (use <= 0 for infinite/no timeout).
    Returns a struct with fields output, exitcode, time
    Exitcode will be negative for signals, 0 for success, positive for other exit codes."""

    # to curb runaway output, cap at 2x solnlen or 100K whichever larger
    # solnlen will be None if executing solution, use 100MB as "unbounded"
    HUGE = 1000000000
    max_output_len = min(max(100000, solnlen*2), HUGE) if solnlen is not None else HUGE

    if logged:
        tmpfile = tempfile.NamedTemporaryFile(delete=True)  # will remove itself from filesystem on close
        command = expand_vars(command, {"logpath": tmpfile.name})
    error_pipe = os.pipe()
    status_pipe = os.pipe()

    # Need detailed comment to explain mchang bash wizardry below
    has_core_cmd = "core_cmd" in command
    if has_core_cmd:  # 2>/dev/null discards bash reporting when core_cmd terminates uncleanly
        to_str = "/usr/bin/timeout -k9 %s" % timeout if timeout else ""
        bash_cmd = 'core_cmd() { { %s "$@"  2>&1 ; } 2>/dev/null ; echo $? >&%d ; return 0; }; { %s ; }' % (to_str, status_pipe[1], command)
    else:
        bash_cmd = '{ %s ; } 2>&1  ' % (command)
    #if gen.NT_RUNNING: print ui.faint("executing: %s" % (bash_cmd))

    child_pid, child_fd = pty.fork()
    if child_pid == 0:  # CHILD HERE
        try:  # blanket try/except to catch any errors when creating/launching child
            os.chdir(wd)
            soft_limit = timeout if timeout else 45
            resource.setrlimit(resource.RLIMIT_CPU, (soft_limit, soft_limit + 15))  # soft limit at timeout, hard timeout 15 seconds more
            try:
                os.setsid() # create a new session, so that we can identify child processes that persist after this process exits
            except OSError:
                pass    # fails if this process is already a process group leader
            signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # get default behavior for sigpipe, http://bugs.python.org/issue1652
            os.dup2(os.open("/dev/null", os.O_RDONLY), 0)  # if attempt read stdin with no redirect, give immediate EOF (otherwise hangs in read)
            os.dup2(error_pipe[1], 2)  # re-route stderr to error_pipe
            os.close(error_pipe[0])    # close all unused pipe ends
            os.close(error_pipe[1])
            os.close(status_pipe[0])
            # -o pipefail to propagate bad exit code from program through pipeline
            # -u to raise error on undefined shell var (default would silently expand to empty)
            # TODO: MC: Remove -u to avoid issues on rice with init script
            args = ["/bin/bash", "-co", "pipefail", bash_cmd]
            combined = dict(os.environ)     # copy existing environment for child
            combined.update(env_overrides)  # merge in any overrides
            combined["SHELL"] = "/bin/bash" # this var necessary in some CS110 situation?
            combined["LC_ALL"] = "C"        # avoid curly quotes from gcc, timeout, and others
            os.execve(args[0], args, combined)
        except Exception:
            # child failed to create/launch, need to tell parent what happened, but... wacky communication channel
            # have to use child process's exitcode and output stream
            traceback.print_exc()   # dump backtrace into child output, can be read by parent
            sys.exit(127)           # child process exits with NO EXEC CODE to indicate failed to launch

    # PARENT HERE
    os.close(error_pipe[1])
    os.close(status_pipe[1])
    if not has_core_cmd: os.close(status_pipe[0])
    util.stty_onclr(child_fd)  # disable pty's translate of LF to CRLF

    starttime = time.time()
    # read all output, read all error (special_read closes the fd once drained)
    output = util.special_read(child_fd, max_output_len)  # child_fd contains child stdout + stderr (and tty) of core_cmd
    # displeasing re.sub, but can't prevent timeout from generating this message when core cmd terminates uncleanly
    if "monitored command dumped core" in output: output = re.sub("(?m)^.*monitored command dumped core.*$", "", output)
    err_out = util.special_read(error_pipe[0], max_output_len)  # error_pipe is where bash/pipeline will report errors
    log = util.read_file(tmpfile.name) if logged else None
    # now wait for child to complete (timeout will kill child if needed)
    bash_status = os.waitpid(child_pid, 0)[1]

    # find any lingering grandchild processes, and kill them
    lingering_pids = subprocess.Popen(['ps', '-s', str(child_pid), '-opid='],
                                      stdout=subprocess.PIPE).communicate()[0].split()
    for pid in lingering_pids:
        subprocess.check_output(['kill', '-9', pid])
    elapsed_time = int(math.ceil(time.time() - starttime))

    bash_exitcode = os.WEXITSTATUS(bash_status) if os.WIFEXITED(bash_status) else -os.WTERMSIG(bash_status)
    # zero exitcode means bash+entire pipeline happy
    # if non-zero, harder to say for sure what happened
    # -o pipefail propagates out non-zero status of any command in pipeline
    # exitcode 1 is used by bash when command didn't parse, but also could be
    # sign of harmless non-success if pipeline had a command that exited 1
    # (such as a grep that didn't match anything...)
    # if any text on stderr, assume that indicates problem otherwise try
    # discern from exit code:
    # accept as ok anything < 126, also ignore 141
    # exitcode 141 means pipe closed, e.g. yes | head -- no big, just ignore

    if len(err_out) or (bash_exitcode >= 126 and bash_exitcode != 141):
        raise TestExecuteError("execute_command '%s' bash error (%d) %s" % (command, bash_exitcode, err_out if err_out else command))

    if not has_core_cmd:
        shellcode = bash_exitcode
    else:
        try:
            shellcode = int(util.special_read(status_pipe[0], 10))  # status_pipe has just exit code of core_cmd
        except ValueError:
            print("WARNING: execute_command unable to read exitcode from status_pipe")
            shellcode = -100

    # when process exited with signal, shell adds 128 to exitcode, so here
    # remap shellcode back to -signum, i.e. shellcode 139 becomes -11 (segv)
    if shellcode in range(128, 128 + signal.NSIG):
        exitcode = 128 - shellcode
    else:
        exitcode = shellcode
    if exitcode == -signal.SIGXCPU: exitcode = TIMED_OUT_CODE  # map XCPU to Timeout code to unify handling later
    return util.Struct(output=output, exitcode=exitcode, time=elapsed_time, log=log)

VAR_REGEX = r"(?<!\\)\$([A-Za-z0-9_]+)"
# VAR_REGEX match $var but not \$var (will not match escaped $ due to negative lookbehind assertion)
# group(0) will be $var, group(1) is var without $

def expand_vars(str, env):
    # for each $var in str, if var in env, replace with env[var] otherwise leave $var unchanged
    return re.sub(VAR_REGEX, lambda m: env[m.group(1)] if m.group(1) in env else m.group(0), str)

def construct_test_from_dict(d):
    asserts.manifest("class" in d, "Test %s doesn't identify which class of test to use" % (d["name"]))
    asserts.manifest(d["class"] in globals(), "Test %s references unknown class named '%s'" % (d["name"], d["class"]))
    factory = globals()[d["class"]]
    asserts.manifest(inspect.isclass(factory) and issubclass(factory, BaseTest), "Test %s %s is not valid subclass of BaseTest" % (d["name"], d["class"]))
    return factory(d)  # pass entire dict as arg to ctor

# Test class hierarchy
# From here down are BaseTest and its subclasses that handle the different
# test varieties (BuildClean, OutputDiffSoln, Valgrind, etc.)

# Test fields are read from ini file, format looks like this:
#  [21-StressSmall]
#  class = OutputDiffSoln
#  command = $reassemble %(filepath)s/alphabet_frags
#  description = reassembles alphabet fragments given as sample
#  timeout = 15
#  totalpts = 4

class BaseTest:

    # These class variables used as the default value if instance/subclass doesn't otherwise shadow/set
    totalpts = 1
    command = None
    description = None
    executables = []
    core_cmd_expansion = "core_cmd"
    # this list controls behavior of simple fail
    exitcodes_to_fail = [-getattr(signal, name) for name in dir(signal) if name.startswith("SIG")] + [TIMED_OUT_CODE]
    is_custom_template = False
    is_interactive = False
    logged = False
    timeout = None

    # Many fields set in the manifest file, e.g. description, timeout, etc.
    # dumped from dictionary to object attributes by ctor
    def __init__(self, fields={}):
        self.name = self.__class__.__name__
        for key in fields:  # add all keys from dict as attributes
            setattr(self, key, fields[key])

    def validate(self):
        asserts.manifest(hasattr(self, "timeout"), "Test %s has no timeout field" % self.name)
        asserts.manifest(self.timeout is None or (isinstance(self.timeout, int) and self.timeout > 0), "Test %s has invalid timeout %s" % (self.name, self.timeout))
        asserts.manifest(not self.command or self.command.count("core_cmd") <= 1, "Test %s command has multiple occurrences of core_cmd" % self.name)
        if hasattr(self, "postfilter"):
            asserts.manifest(self.postfilter in globals(), "Test %s has postfilter '%s', no such function found (missing from grading.py file?)" % (self.name, self.postfilter))
        asserts.manifest(isinstance(self.totalpts, int), "Test %s has invalid totalpts %s" % (self.name, self.totalpts))

    def command_for_display(self, for_soln=False):
        if self.command:
            # expand command, but delete the "core_cmd" call, what is printed will mostly copy/paste to shell
            env = self.soln_env() if for_soln else self.local_env()
            return self.expanded_command(env).replace("core_cmd ", "")

    def expanded_command(self, env):
        if "$core_cmd" in self.command:
            explicit = self.command
        else:   # make implicit->explicit, add $core_cmd in front of $executable
            prefixed_executables = {ex: "$core_cmd $%s" % ex for ex in self.executables}
            explicit = expand_vars(self.command, prefixed_executables)
        return expand_vars(explicit, env)  # expands $core_cmd and $executable

    def local_env(self):
        d = {ex: os.path.join(".", ex) for ex in self.executables}
        d["core_cmd"] = self.core_cmd_expansion
        return d

    def run(self, path, context, noisy=True, repo=None):
        noisy = noisy and context in [FOR_AUTOGRADER, FOR_RUNTESTS, FOR_SANITY]
        """Run the test object on the submission at the given path.  Executes
        command and scores result. Returns Result object"""
        if noisy:
            print "\n+++ Test %s on %s" % (ui.bold(self.name), gen.shortpath(path))
            if self.description: print "Descr:   %s" % self.description
            if self.command: print "Command: %s" % self.command_for_display()
        try:
            r = self.execute_and_score(path, context, repo)
        except KeyboardInterrupt:  # if cntrl-c during test execution
            if context in [FOR_SANITY, FOR_RUNTESTS, FOR_TESTSUITE, FOR_DRYRUN]: raise  # propagate up to quit
            r = results.Deferred()    # interrupted during batch grade, just defer the test
        r.set_test(self)  # not pretty, but lets Result obj know test information
        if noisy:
            print r.string_for_context(context)
        return r

    def execute_local(self, wd):
        return execute_command(wd, self.expanded_command(self.local_env()), timeout=self.timeout, logged=self.logged)

    def execute_and_score(self, path, context, repo):
        """Executes command, handles simple failures (timeout, signal), filters output and passes to score.
        Can override here if need different execute+score handling, more typical to just override score"""
        student_ex = self.execute_local(path)
        failed = self.simple_fail(student_ex)  # pick off obvious failure cases
        if failed is not None: return failed
        student_ex.output = self.filter(student_ex.output)
        return self.score(student_ex, context)

    def score(self, student_ex, context):
        """Given student execution info, return scored result"""
        # my attempt to fake abstract method, surely there is some better way to do this
        assert(0), "no implementation of abstract score() method in class %s" % self.__class__.__name__

    def simple_fail(self, ex, codes_to_fail=None):
        """Picks off programs that timed out, terminated with signal, or failed to
        execute in shell.  Zero and other exit codes pass through."""
        # TODO: JDZ work out the codes to fail dance -- kind of a mess
        if codes_to_fail is None: codes_to_fail = self.exitcodes_to_fail
        if ex.exitcode in NO_EXEC_CODES:  # these code are always a problem, should never ignore
            return results.NoExecute(msg="(%d) %s" % (ex.exitcode, ex.output))
        if ex.exitcode not in codes_to_fail:
            return None
        libc_regexes = "|".join(["\*\*\* Error in `.* \*\*\*", "\*\*\* .* \*\*\*: .* terminated"])
        if ex.exitcode == TIMED_OUT_CODE:
            # some of the malloc errors end up in deadlock and hit timeout
            msg = util.match_regex(libc_regexes, ex.output)
            return results.TimedOut(limit=self.timeout if self.timeout else ex.time, solntime=self.soln_time if hasattr(self, "soln_time") else None, errmsg=msg)
        elif ex.exitcode < 0:
            str = scoring.signal_string(-ex.exitcode)
            if -ex.exitcode == signal.SIGABRT:
                assertmsg = util.match_regex(".*Assertion.*failed\.", ex.output)
                libcmsg = util.match_regex(libc_regexes, ex.output)
                str += ((" %s" % assertmsg) if assertmsg else "") + ((" %s" % libcmsg) if libcmsg else "")
            return results.SignalRaised(signal_string=str)
        else:
            return None

    def filter(self, str):
        """If postfilter set, run filter on output before feeding into score()"""
        if not str or not hasattr(self, "postfilter"): return str
        return globals()[self.postfilter](str)    # invoke method by string name, gotta love python!

    def __repr__(self):
        return "<Test %s>" % self.name

    def __str__(self):  # to allow pretty-print of test object
        return self.name

class VersusSolution(BaseTest):
    cache_soln_output = True
    cached_soln_ex = None

    def score(self, student_ex, soln_ex, context):
        """Given student and soln execution info, return scored result"""
        # my attempt to fake abstract method, surely there is some better way to do this
        assert(0), "no implementation of abstract score() method in class %s" % self.__class__.__name__

    def execute_and_score(self, path, context, repo):
        """Executes command, handles simple failures (timeout, signal), filters output and passes to score.
        Can override here if need different execute+score handling, more typical to just override score"""
        soln_ex = self.use_or_create_soln_cache(path) if self.cache_soln_output else self.execute_solution(path)
        student_ex = self.execute_local(path)
        failed = self.simple_fail(student_ex)  # pick off obvious failure cases
        if failed is not None: return failed
        student_ex.output = self.filter(student_ex.output)
        soln_ex.output = self.filter(soln_ex.output)
        return self.score(student_ex, soln_ex, context)

    def execute_local(self, wd):
        solnlen = len(self.cached_soln_ex.output) if self.cached_soln_ex else -1
        return execute_command(wd, self.expanded_command(self.local_env()), timeout=self.timeout, logged=self.logged, solnlen=solnlen)

    def execute_solution(self, wd):
        # we execute the solution with working dir = submission, not sure if this is a good idea
        # previously always used self.filepath as cwd, but keeping that way forces custom tests to deal with different
        # context for relative paths...
        #import pdb; pdb.set_trace()
        try:
            soln_ex = execute_command(wd, self.expanded_command(self.soln_env()), timeout=self.timeout, logged=self.logged, solnlen=None)
            soln_error = self.simple_fail(soln_ex)
            if soln_error: raise Exception(soln_error.summary_string())
        except Exception as e:
            # repackage as SolutionError in hopes to make it obvious to student this is our problem, not theirs
            cmd = self.command_for_display(for_soln=True)
            raise SolutionError("Unable to run %s\n[%s]" % (cmd, str(e)))
        return soln_ex

    def soln_env(self, soln_path=None):
        if soln_path is None: soln_path = self.filepath
        d = {ex: os.path.join(soln_path, "%s_soln" % ex) for ex in self.executables}
        d["core_cmd"] = self.core_cmd_expansion
        return d

    def read_soln_cache(self):
        cached_output_path = os.path.join(self.filepath, "soln_output", self.name)
        if os.path.exists(cached_output_path):  # cached file exists, now check and see if it's up-to-date
            try:
                # -L means follow symlink and test on actual reference
                # if any file in grade subdir (not subdirs) is newer than cache (rejects if any
                # updates to manifest, solution executables, input files, and so on)
                findcmd = "find -L %s -maxdepth 1 -cnewer %s | wc -l" % (self.filepath, cached_output_path)
                nfiles_newer = int(commands.getstatusoutput(findcmd)[1])
                if nfiles_newer == 0:
                    output = util.read_file(cached_output_path)
                    logname = "%s-%s" % (self.__class__.__name__.upper(), self.name[:2])
                    log = util.read_file(os.path.join(self.filepath, "soln_output", logname))  # returns None if file not exist
                    if self.logged and not log: return None  # if only have output and not log, then refresh both
                    return util.Struct(output=output, log=log, time=-1, exitcode=0)  # JDZ faking soln time and exitcode, will this be problem?
            except:
                pass  # if find command fails, assume stale
        return None

    def write_soln_cache(self, ex):
        if gen.is_instructor():  # only update cached solution file if I'm executing script (lame locking strategy)
            if "grade" in os.path.basename(self.filepath):  # no cache output for sanity, only grade
                cached_output_path = os.path.join(self.filepath, "soln_output", self.name)
                util.write_file(ex.output, cached_output_path, makeparent=True)
                if ex.log:
                    logname = "%s-%s" % (self.__class__.__name__.upper(), self.name[:2])
                    util.write_file(ex.log, os.path.join(self.filepath, "soln_output", logname), makeparent=True)

    def use_or_create_soln_cache(self, wd):
        if not self.cached_soln_ex:
            self.cached_soln_ex = self.read_soln_cache()
            if not self.cached_soln_ex:
                fresh = self.execute_solution(wd)
                self.write_soln_cache(fresh)
                self.cached_soln_ex = fresh
        # cached version has raw (unfiltered) output
        # work on a copy so filter now won't interfere with later use of cache
        return copy.copy(self.cached_soln_ex)

class BuildClean(BaseTest):
    description = "verify project builds cleanly"
    command = "make clean && make"
    timeout = None

    def execute_local(self, wd):
        # JDZ to fix, consider how to jam env GCC_COLORS= ahead of make and no need to strip colors later
        student_ex = BaseTest.execute_local(self, wd)
        # shell/valgrind require cexecute permission (unix chmod, not afs) to execute, force +x on all executables
        util.system_quiet("chmod -f a+x " + " ".join([os.path.join(wd, ex) for ex in self.executables]))
        return student_ex

    def score(self, student, context):
        txt = ui.stripcolors(student.output)  # avoid any colorization messing with my simple-minded grep
        errors_and_warnings = "\n".join(util.grep_text("error:|warning:|note:", txt))

        if student.exitcode == 0 and not errors_and_warnings:
            return results.Correct(score=self.totalpts, short="Clean build")
        else:
            return results.BuildIssue(score=0, is_error=student.exitcode != 0, detail=errors_and_warnings)

    def run(self, path, context, noisy=True, repo=None):
        # override and halt sanity check on build failure -- only sadness will follow...
        r = BaseTest.run(self, path, context, noisy, repo)
        build_fail = isinstance(r, results.BuildIssue) and r.is_error
        if context in [FOR_SANITY, FOR_TESTSUITE] and build_fail:
            print ui.bold("\nBuild failed! Continuing with sanity check may not be reliable.")
            ui.confirm_or_exit("Continue anyway?")
        return r

class ClangTidy(BuildClean):
    description = "run automated code style checks"
    command = "make tidy"
    timeout = None

    def score(self, student, context):
        txt = ui.stripcolors(student.output)  # avoid any colorization messing with my simple-minded grep
        errors_and_warnings = "\n".join(util.grep_text("error:|warning:|note:", txt))

        if student.exitcode == 0 and not errors_and_warnings:
            return results.Correct(score=self.totalpts, short="Clean run")
        else:
            message = ">> Some automated style checks failed. You aren't guaranteed to lose points for this, but you should probably try fixing these issues. Run \"make tidy\" to rerun the style checks."
            return results.BuildIssue(score=0, is_error=student.exitcode != 0, detail=message + '\n\nmake tidy output:\n' + student.output)

class OutputDiffSoln(VersusSolution):
    match_ratio = 1.0  # match_ratio is from 0 to 1 (exact match), accept when match >= ratio
    detail = None  # when set to non-empty, controls how the detail is reported (diff output/correct)

    def score(self, student, soln, context):
        return scoring.score_output_match(student.output, soln.output, self.totalpts, context, ratio=self.match_ratio, detail=self.detail)

class GracefullyHandled(VersusSolution):
    expected_behavior = "Feedback to user should be clear, specific, and actionable"
    attempted_action = None
    reject = None
    msg_regex = None  # assign regex, dryrun auto-scores correct if wording matches regex
    accept_ratio = .95  # can accept fuzzy-match to our solution's message, default is 95% (use 1.0 to accept exact match only)

    exitcodes_to_fail = []
    # stop simple_fail from picking off bad exits (crash/abort/timeout), drop through to grader for partial credit

    def validate(self):
        VersusSolution.validate(self)
        asserts.manifest(self.attempted_action is not None, "GracefullyHandled test %s has no attempted_action" % self.name)

    def score(self, student, soln, context):
        # Can override and provide custom options to prompt grader
        return self.score(student, soln, context, provided_options=None)

    def score(self, student, soln, context, provided_options=None):
        if self.reject and scoring.match_ok(student.output, self.reject, accept_ratio=self.accept_ratio):  # reject can be set to known-wrong output & picked off here
            return results.Incorrect(score=0, short="Error undetected; no handling demonstrated")

        message_ok = scoring.match_ok(student.output, soln.output, accept_ratio=self.accept_ratio)   # match or very close to our wording
        clean_exit = (student.exitcode >= 0 and student.exitcode not in [124, 126, 127])

        if message_ok and clean_exit:
            return results.Correct(score=self.totalpts, short="Submission feedback and handling matches sample")

        if context in [FOR_DRYRUN, FOR_TESTSUITE]:
            # for dryrun, autoscore bad exits as failure
            failed = self.simple_fail(student, VersusSolution.exitcodes_to_fail)
            if failed is not None: return failed
            if self.msg_regex and util.match_regex(self.msg_regex, student.output):
                return results.Correct(score=self.totalpts, short="Matched dryrun regex")
            elif not clean_exit:
                return results.Incorrect(score=0, short=scoring.summarize_exit_status(student.exitcode))
            else:
                return results.Inconclusive(short='', detail=ui.abbreviate(student.output, maxlines=3) if student.output else "<empty>")
        if len(soln.output) > 1000: soln.output = soln.output[:1000] + "..."  # abbreviate output if v. long (infinite loop?)

        if context == FOR_PREGRADE:
            return results.Deferred()   # postpone to interactive grader
        else:
            return scoring.score_handling(self.attempted_action, self.expected_behavior, student, soln, clean_exit, self.totalpts, self.accept_ratio, provided_options=provided_options)

class WrappedWithLogFile(VersusSolution):
    logged = True

    def simple_fail(self, ex, codes_to_fail=None):
        err_result = VersusSolution.simple_fail(self, ex, codes_to_fail)
        if err_result: return err_result
        # if log file was not created or empty, it is a failure
        if ex.log is None:
            return results.NoExecute(msg="(no log file created)")
        return None


class Valgrind(WrappedWithLogFile):
    description = "verify clean run under valgrind, should be no errors nor leaks"
    reject_regex = None
    leakpts = None

    # leak-check=summary reports summary without individual leaks & won't count leaks as errors (which happens on leak-check=full)
    # added --trace-children=yes added so will follow through exec (i.e. env blah $hello)
    # TODO JDZ (someday/never)logging is problematic if program uses fork, need separate log files by pid, ugh
    core_cmd_expansion = "core_cmd /usr/bin/valgrind --trace-children=yes --tool=memcheck --leak-check=summary --show-reachable=yes --error-exitcode=%s --log-file=$logpath" % (VALGRIND_ERROR_CODE)

    def validate(self):
        WrappedWithLogFile.validate(self)
        asserts.manifest(isinstance(self.leakpts, int), "Valgrind test %s has invalid leakpts '%s'" % (self.name, self.leakpts))
        self.verify_valgrind_version()

    # We scrape the Valgrind output, so are v. sensitive to changes in text being printed, the version check
    # here will remind you to check whether a version change requires new tweaks
    def verify_valgrind_version(self):
        # MC: I know this is really not the right place to put this...
        if gen.MC_RUNNING: return
        expected = ["valgrind-3.10.0.SVN", "valgrind-3.10.1", "valgrind-3.11.0", "valgrind-3.15.0"]
        output = commands.getoutput("/usr/bin/valgrind --version")
        assert(output in expected), "Valgrind version '%s' does not match expected %s." % (output, ui.pretty_list(expected))

    def simple_fail(self, ex, codes_to_fail=None):
        """Catch weird interaction between Valgrind and certain errors. Valgrind makes special case of
        some libc aborts, writes error message into Valgind report, program terminate, exitcode 127
        (gleaned from Valgrind src: special case is buffer overflow strcpy/memcpy/memmove)"""
        # Note that we need to check for this BEFORE inherited version (which treats 127 as no execute)
        if ex.exitcode == 127 and ex.log:  # no exec yet wrote log? something is definitely up...
            error_msg = util.match_regex("\*\*\d+\*\*\s+(.*)", ex.log)  # match line labelled **pid**
            if error_msg: return results.SignalRaised(signal_string=error_msg)
        return WrappedWithLogFile.simple_fail(self, ex, codes_to_fail)

    def score(self, student, soln, context):
        return scoring.score_valgrind(student.output, soln.output, self.reject_regex, student.log, student.exitcode, self.leakpts, self.totalpts - self.leakpts, context)

class MemoryUse(Valgrind):
    description = "verify reasonably efficient in use of memory"
    multiplier = 3
    leakpts = 0
    core_cmd_expansion = "core_cmd /usr/bin/valgrind --trace-children=yes --tool=memcheck --leak-check=summary --error-exitcode=%s --log-file=$logpath" % VALGRIND_ERROR_CODE

    def score(self, student, soln, context):
        return scoring.score_memory_use(student.output, soln.output, self.reject_regex, soln.log, student.exitcode, student.log, self.totalpts, self.multiplier, context)


class Callgrind(Valgrind):
    description = "count instructions"
    core_cmd_expansion = "core_cmd /usr/bin/valgrind --tool=callgrind --error-exitcode=%s --log-file=$logpath" % VALGRIND_ERROR_CODE

    def score(self, student, soln, context):
        return scoring.score_memory_use(student.output, soln.output, self.reject_regex, soln.log, student.exitcode, student.log, self.totalpts, self.multiplier, context)


class TimeUse(WrappedWithLogFile):
    description = "verify reasonably efficient run time performance"
    multiplier = 3
    reject_regex = None
    soln_time = None
    core_cmd_expansion = "core_cmd /usr/bin/time -p -o $logpath"

    def __init__(self, items={}):
        WrappedWithLogFile.__init__(self, items)
        self.timeout = (self.multiplier+2)*self.soln_time  # slightly more generous timeout, anything past multiplier is rejected as too pokey

    def validate(self):
        WrappedWithLogFile.validate(self)
        asserts.manifest(isinstance(self.soln_time,int), "TimeUse test %s has invalid soln_time %s" % (self.name, self.soln_time))

    def score(self, student, soln, context):
        return scoring.score_time_use(student.output, soln.output, student.log, self.reject_regex, student.exitcode, self.soln_time, self.totalpts, self.multiplier, context)

class CustomOutputDiffSoln(OutputDiffSoln):
    # This is the test class used when students list their own cases for custom sanity check
    # Behavior is mostly OutputDiffSoln but with a few tweaks:
    # if restrict_executables True, has to use executable named in manifest list
    # if restrict_executables False, can name their own executables (e.g. for cvec/cmap client programs)
    # for non-restricted executables, will access matching soln in student cwd instead of samples
    # student timeout is set as 5x what the sample took
    is_custom_template = True
    restrict_executables = True
    timeout = None

    def init_from_string(self, line, num):
        self.name = "Custom-%d" % num
        command_str = line.strip()  # remove leading/trailing whitespace
        # if exec_name begins with ./  just discard (will allow either name or ./name as convenience)
        if command_str.startswith("./"): command_str = command_str[2:]

        # allow students to use $executable to position somewhere other than first in custom test command
        matched = util.match_regex(VAR_REGEX, command_str)
        if matched:
            exec_name = matched
            self.command = "$core_cmd " + command_str
        else:
            exec_name = command_str.split()[0]  # break off first token
            # prepend $ onto executable name to use as shell variable (yes, this is a hack)
            self.command = "$" + command_str
        # if template restricts to a list of valid executables, reject exec name not on list
        assert(exec_name in self.executables or not self.restrict_executables), "%s is not a valid executable choice, instead use one of %s" % (exec_name, ui.pretty_list(self.executables))
        assert(re.match("^[A-Za-z0-9_]+$", exec_name)), "%s is not a valid executable name" % (exec_name)
        if exec_name not in self.executables:
            self.executables = [exec_name]
            self.soln_path = "."
        else:
            self.soln_path = self.filepath
        return self

    def soln_env(self):
        return OutputDiffSoln.soln_env(self, soln_path=self.soln_path)

    def execute_solution(self, wd):
        self.timeout = None  # temporarily set timeout to let solution run to completion
        soln_ex = OutputDiffSoln.execute_solution(self, wd)
        self.timeout = 5*soln_ex.time  # set timeout to be 5x what solution took
        return soln_ex

class GraderReview(BaseTest):
    is_interactive = True
    description = "grader review of submission"

    def __init__(self, items={}):
        BaseTest.__init__(self, items)
        wr = self.review_template()
        self.totalpts = wr.points_possible()

    def review_template(self):
        return WebReview.read_template(self.filepath)

    def validate(self):
        BaseTest.validate(self)
        self.review_template()  # will validate template

    def do_review(self, repo):
        # can override in subclass for diff behavior before/after/instead of browser
        WebReview.grade_in_browser(repo)

    def pregrade(self, wr, repo):
        # can override in subclass for pregrade behavior (e.g. scrape)
        pass

    def execute_and_score(self, path, context, repo):
        if context in [FOR_PREGRADE, FOR_AUTOGRADER]:
            wr = WebReview.create(path, self.filepath)  # force create from template if needed
            self.pregrade(wr, repo)
        if context in [FOR_AUTOGRADER]:
            self.do_review(repo)
        wr = WebReview.load(path)  # will not create from template if not already there
        if wr:
            return results.ParseWebReview(path=path, has_points=wr.has_points(), has_buckets=wr.has_buckets())
        else:
            return results.Deferred()

class ExpectedOutput(BaseTest):
    required_exit_code = None
    incorrect_message = "Incorrect"

    def execute_and_score(self, path, context, repo):
        student = self.execute_local(path)
        failed = self.simple_fail(student)
        if failed is not None: return failed

        if self.required_exit_code and student.exitcode != self.required_exit_code:
            return results.Incorrect(score=0, short=self.incorrect_message)
        if self.expected_output and not scoring.match_ok(student.output, self.expected_output):
            return results.Incorrect(score=0, short=self.incorrect_message)
        return results.Correct(score=self.totalpts, short="Correct")
