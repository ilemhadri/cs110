
"""
Julie Zelenski, 2009-present
Ryan Noon, original design

The scoring module has the functions for all varieties of scoring.
 -- Some scoring is just output-diff comparison
 -- Others are scraped from time/Valgrind reports
 -- Some require interaction from TA (to evaluate quality)
"""

import collections, commands, difflib, math, re, signal, tempfile
import diff_match_patch, gen, results, testing, ui, util

def half_floor(val):
    return int(math.floor(float(val)*0.5))

def half_ceil(val):
    return int(math.ceil(float(val)*0.5))

# find signal name for code via inverse lookup on signal attributes (cheesy? but cool!)
def name_for_signal(code):
    for name in dir(signal):
        if name.startswith("SIG") and getattr(signal, name) == code:
            return name
    return None

def signal_string(code):
    return "%d (%s)" % (code, name_for_signal(code))

def summarize_exit_status(exitcode):
    """returns string describing termination behavior based on exit code"""
    if exitcode == 0:
        return "exited cleanly"
    if exitcode == testing.TIMED_OUT_CODE:
        return "timed out and was forcibly killed"
    elif exitcode < 0:
        return "terminated with signal %s" % signal_string(-exitcode)
    else:
        return "exited with non-zero code %d" % exitcode

def summarize_output(output, exitcode):
    """Neatly summarizes output from program with exit status"""
    summary = "----- Submission output:\n%s\n" % ui.blue(output)
    exited = "----- Program %s." % summarize_exit_status(exitcode)
    summary += ui.red(exited) if exitcode < 0 else exited  # highlight non-clean exit with red text
    return summary

def summarize_execution(output, soln_output, exitcode):
    if match_ok(output, soln_output):
        if exitcode >= 0: return None
        summary = ''
    else:
        summary = "Submission produced incorrect output"
    if exitcode != 0 and exitcode != testing.VALGRIND_ERROR_CODE:
        summary += " (%s)" % summarize_exit_status(exitcode)
    return summary

def copy_to_temp_file(str):
    file = tempfile.NamedTemporaryFile(mode='w', dir="/tmp")
    file.write(str.strip())
    file.write('\n')     # add trailing newline makes diff happy
    file.flush()
    # file is left open (closing will delete it, caller must close)
    return file

# python difflib won't work because no option to ignore/coalese whitespace,
# so write to files and invoke diff command at shell using -B -b flags
def diff_ignoring_white_old(str1, str2, options=''):
    tmp1 = copy_to_temp_file(str1)
    tmp2 = copy_to_temp_file(str2)
    # -T puts tabs in front of diff lines
    result = commands.getoutput("diff -B -b -T -a %s %s %s" % (options, tmp1.name, tmp2.name))
    tmp1.close()
    tmp2.close()
    return result

def diff_ignoring_white(str1, str2, options=''):
    old_version = diff_ignoring_white_old(str1, str2, options)
    if old_version == '': return old_version
    dmp = diff_match_patch.diff_match_patch()
    diffs = dmp.diff_main(str1, str2)
    dmp.diff_cleanupSemantic(diffs)
    return ui.pretty_diffs(dmp, diffs)

def diff_test(str1, str2, options=''):
    tmp1 = copy_to_temp_file(str1)
    tmp2 = copy_to_temp_file(str2)
    # -T puts tabs in front of -Blines
    result = commands.getoutput("diff -B -b -T %s %s %s" % (options, tmp1.name, tmp2.name))
    tmp1.close()
    tmp2.close()
    return result

def match_ok(output, expected_output, accept_ratio=1.0):
    """Does the output match the expected output?  Returns boolean"""
    if diff_ignoring_white(output, expected_output) == '':
        return True
    if False and gen.JZ_RUNNING:
        print accept_ratio
        print ui.green(expected_output)
        print ui.blue(output)
        print ui.red(diff_ignoring_white(output, expected_output))
    if accept_ratio >= 1.0 or accept_ratio <= 0: return False
    # if ok to be "close", use fuzzy match algorithm
    # sequence matcher has 'junk' filtering, but weird, want to ignore whitespace so remove first
    output_nowhite = output.translate(None, " \t")
    expected_nowhite = expected_output.translate(None, " \t")
    s = difflib.SequenceMatcher(None, output_nowhite, expected_nowhite)
    # reject above ratio
    return s.ratio() > accept_ratio

Option = collections.namedtuple("Option", "score, text, explanation, concern, prompt")
Option.__new__.__defaults__ = (None, False)  # sets values for last 2 fields, they will be optional to init

def get_score_from_options(output, describe_output, options):
    """ Options should be a list of Option namedtuples (see definition above)
    If option.concern is not None, it is a reason that suggests this option might not apply, in which
    attempt to choose it is challenged before confirming"""
    print "%s\n%s" % (output, describe_output)
    llist = ["%s (%s)" % (opt.text, opt.explanation) for opt in options]
    (index, comment) = ui.get_lettered_choice(llist, allow_comment=True)
    chosen = options[index]
    if chosen.concern:
        print ui.red("Are you sure? %s" % chosen.concern)
        (index, comment) = ui.get_lettered_choice(llist, allow_comment=True)
        chosen = options[index]
    reason = chosen.text + (" (%s)" % comment if comment else '')
    if chosen.prompt:  # ask grader for specific feedback
        comment = raw_input("Enter comment for student: ").strip()
        if comment != '': reason = comment
    return (chosen.score, reason)

def score_handling(attempted_action, expected_behavior, student, soln, clean_exit, pts, ratio, provided_options=None):
    """ Used to evaluate results from situations requiring graceful handling (i.e. missing/wrong args)"""

    concern = "This submission %s." % summarize_exit_status(student.exitcode) if not clean_exit else None
    options = provided_options(pts) if provided_options is not None else [Option(pts, "Gives feedback that is correct/clear/actionable and handles appropriately", "print err msg, clean exit", concern),
               Option(half_floor(pts), "Gives feedback that is correct/clear/actionable but handles incorrectly", "blunders on, extraneous actions/printing, crash/abort"),
               Option(half_floor(pts), "Gives feedback that is misleading/vague/unhelpful but handles appropriately", "print err msg, clean exit", concern),
               Option(0, "Gives feedback that is misleading/vague/unhelpful and handles incorrectly", "blunders on, extraneous actions/printing, crash/abort"),
               Option(0, "Gives no feedback on error; no handling demonstrated", "error not detected at all?")]

    if match_ok(student.output, soln.output, accept_ratio=ratio):  # pick off those that match or very close to our wording here
        if clean_exit:
            (score, reason) = (options[0].score, options[0].text) # TODO: jdz I don't think these come here any more
        else:
            (score, reason) = (options[1].score, options[1].text)
    elif not student.output:
        (score, reason) = (options[4].score, options[4].text)   # if no output at all, autoscore
    else:
        (score, reason) = get_score_from_options(summarize_output(student.output, student.exitcode), "Above is the output from %s. %s.\n(soln uses '%s')" % (attempted_action, expected_behavior, soln.output), options)
    if score == pts:
        return results.Correct(score=pts, short=reason)
    else:
        if clean_exit:
            addl = ''
        else:
            addl = "; %s" % summarize_exit_status(student.exitcode)
        return results.Incorrect(score=score, short=reason + addl)

def score_output_match(output, correct_output, pts, context, ratio=1.0, detail=None):
    if match_ok(output, correct_output, accept_ratio=ratio):
        return results.Correct(score=pts, short="Submission output matches sample", matched_output=output if context == testing.FOR_SANITY else None)
    return results.MismatchOutput(score=0, output=output, correct_output=correct_output,
                                  detail=results.summarize_mismatch(output, correct_output, detail))

# This is currently matched to the output from Valgrind version 3.5.0 and 3.7.0
# Be warned this when versions are updated you may have to tweak
def scrape_valgrind_report(valgrind_log, exitcode):
    summary = util.Struct(internal_error=None, errors=None, leaks=None)

    # previously compared exitcode == 1 to detect if valgrind itself crashed (but also == 1 if program exited 1), instead look for internal error txt in log
    if "report this bug to: www.valgrind.org" in valgrind_log:  # if internal error caused valgrind to crash
        return util.Struct(internal_error="submission crashed Valgrind")
    if "Valgrind's memory management: out of memory" in valgrind_log:
        return util.Struct(internal_error="submission exhausted Valgrind address space")
    if "Fatal error at startup" in valgrind_log:
        return util.Struct(internal_error="fatal error on Valgrind startup (no 32bit cross compile?)")

    error_free = (exitcode != testing.VALGRIND_ERROR_CODE and " 0 errors from 0 contexts" in valgrind_log)
    if not error_free:
        vg_errors = "\n".join(util.grep_text("Conditional|Invalid|uninitialised|Address|destination overlap", valgrind_log))
        summary.errors = util.match_regex("(==\d+==\s+ERROR SUMMARY.*)", valgrind_log) + "\n" + vg_errors
        if not summary.errors:
            return util.Struct(internal_error="malformed Valgrind log (could not scrape ERROR SUMMARY)")

    leak_free = ("All heap blocks were freed -- no leaks are possible" in valgrind_log)
    if not leak_free:
        leaks = util.match_regex("(?s)(==\d+==\s+LEAK SUMMARY.*)==\d+==\s+\n", valgrind_log)  # (?s) flag is DOTALL to pick up newlines to end of report
        if not leaks:
            return util.Struct(internal_error="malformed Valgrind log (could not scrape LEAK SUMMARY)")
        real_leaks = False
        for leaktype, nbytes in util.grep_text("\s+([\w\s]+): ([\d,]+) bytes", leaks, 1, 2):
            if leaktype == "suppressed" or nbytes == "0": continue
            real_leaks = True
        if real_leaks:
            summary.leaks = util.match_regex("(?s)(==\d+==\s+LEAK SUMMARY.*)==\d+==\s+\n", valgrind_log)  # (?s) flag is DOTALL to pick up newlines to end of report
    try:
        summary.str = util.match_regex("total heap usage(.*bytes allocated)", valgrind_log)
        nallocs = util.match_regex("((\d|,)+) allocs,", summary.str)
        summary.nallocs = int(ui.without_commas(nallocs))
        nbytes = util.match_regex("((\d|,)+) bytes allocated", summary.str)
        summary.nbytes = int(ui.without_commas(nbytes))
    except Exception:
        return util.Struct(internal_error="malformed Valgrind log (could not scrape total heap usage)")

    return summary

def score_valgrind(output, soln_output, reject_regex, valgrind_log, exitcode, leakpts, errorpts, context):
    valgrind = scrape_valgrind_report(valgrind_log, exitcode)
    execution_errors = summarize_execution(output, soln_output, exitcode)

    if valgrind.internal_error:
        return results.Incorrect(short="Unable to evaluate memory correctness %s" % valgrind.internal_error)
    if reject_regex is not None and re.match(reject_regex, output):
        return results.Inconclusive()
    if execution_errors and (not valgrind.errors or not valgrind.leaks):  # report would earn some points, but run was fishy, verify "good faith"
        if context in [testing.FOR_DRYRUN, testing.FOR_TESTSUITE]:  # just return score 0 with summary of findings if non-interactive
            return results.Inconclusive(short=execution_errors)
        if context == testing.FOR_PREGRADE:
            return results.Deferred()  # requires judgment, defer

        print ui.red("We got a Valgrind report, but execution errors cast doubt on its reliability.")
        print ui.bold("Errors: ") + ui.blue(execution_errors)
        if "incorrect output" in execution_errors and ui.get_yes_or_no("Do you want to view the discrepancy in output?"):
            print results.summarize_mismatch(output, soln_output)
        if ui.get_yes_or_no("Do you want to view the Valgrind report?"):
            print ui.blue(valgrind_log)
        options = [Option(1, "code seems complete and program executed in full", "Valgrind report should be reliable"),
                   Option(0, "incomplete code and/or incomplete execution", "Valgrind report is inconclusive")]
        (score, reason) = get_score_from_options("", "Should we trust the Valgrind report for this run?", options)
        if score == 0:  # report is unreliable, result is inconclusive
            return results.Inconclusive()

    # execution errors were none or dismissed, use scrape of Valgrind report as truth
    if valgrind.errors and valgrind.leaks:
        return results.MemBoth(score=0, detail=valgrind.errors + '\n' + valgrind.leaks + '\n')
    elif valgrind.errors:
        return results.MemError(score=leakpts, detail=valgrind.errors + '\n')
    elif valgrind.leaks:
        return results.MemLeak(score=errorpts, detail=valgrind.leaks + '\n')
    else:
        return results.Correct(score=leakpts+errorpts, short="Valgrind report was clean")

def score_memory_use(output, soln_output, reject_regex, soln_log, exitcode, valgrind_log, pts, multiplier, context):
    soln = scrape_valgrind_report(soln_log, 0)
    if soln.internal_error:
        print soln_log
        raise Exception("Unable to scrape solution's memory use for efficiency comparison. Tell Julie! (%s)" % soln.internal_error)

    execution_errors = summarize_execution(output, soln_output, exitcode)
    valgrind = scrape_valgrind_report(valgrind_log, exitcode)
    if valgrind.internal_error:
        return results.Incorrect(short="Unable to evaluate memory use %s" % valgrind.internal_error)

    if reject_regex is not None and re.match(reject_regex, output):
        return results.Inconclusive()

    soln.nbytes = max(1, soln.nbytes)
    soln.nallocs = max(1, soln.nallocs)
    ratio = float(valgrind.nbytes)/soln.nbytes
    ratio2 = float(valgrind.nallocs)/soln.nallocs
    if ratio > multiplier:
        over = "Memory use %s bytes is %.1fx soln " % (ui.with_commas(valgrind.nbytes), ratio)
    elif ratio2 > multiplier:
        over = "Memory use %s allocs is %.1fx soln " % (ui.with_commas(valgrind.nallocs), ratio2)
    else:
        over = None
    if (context == testing.FOR_DRYRUN and (ratio > 1.5 or ratio2 > 1.5)):  # just so I can see what is happening
        msg = "Memory use %s bytes is %.1fx soln, %s allocs is %.1fx solution " % (ui.with_commas(valgrind.nbytes), ratio, ui.with_commas(valgrind.nallocs), ratio2)
    else:
        msg = None
    if execution_errors and not over:  # mem use ok, but run was fishy, verify "good faith"
        if context in [testing.FOR_DRYRUN, testing.FOR_TESTSUITE]:  # just return score 0 with summary of findings if non-interactive
            return results.Inconclusive(short="Memory use (%s bytes is %.1fx soln) %s" % (ui.with_commas(valgrind.nbytes), ratio, execution_errors))
        if context == testing.FOR_PREGRADE:
            return results.Deferred()  # requires judgment, defer to interactive grader
        print "Submission uses: %s\nSolution uses:   %s" % (ui.blue(valgrind.str), soln.str)
        print ui.red("Memory usage ok (within %sx of solution), but run had execution errors that cast doubt on report's reliability." % multiplier)
        print ui.bold("Errors: ") + ui.blue(execution_errors)
        if "incorrect output" in execution_errors and ui.get_yes_or_no("Do you want to view the discrepancy in output?"):
            print results.summarize_mismatch(output, soln_output)
        options = [Option(1, "code seems complete and program executed in full", "memory usage should be reliable"),
                   Option(0, "incomplete code and/or incomplete execution", "memory usage is inconclusive")]
        (score, reason) = get_score_from_options("", "Should we trust the memory usage reported for this run?", options)
        if score == 0:  # report is unreliable, result is inconclusive
            return results.Inconclusive()

    # from here, use scrape of Valgrind mem usage as truth
    if not over:
        if not msg:
            return results.Correct(score=pts, short="Passed, memory use on par with expectation")
        else:
            return results.TooMuch(score=pts, short=msg)
    else:
        summary = over
        if execution_errors is not None: summary += execution_errors
        return results.TooMuch(short=summary)

def scrape_time_report(timelog):
    summary = util.Struct(internal_error=None)
    try:
        nsecs = util.match_regex("(?s)real.*user\s+(\d+\.\d+).*sys", timelog, 1)  # use ?s for DOTALL
        summary.nsecs = float(nsecs)  # extract user time number
    except Exception:
        summary.internal_error = "malformed time result"
    return summary

def score_time_use(output, soln_output, timelog, reject_regex, exitcode, soln_time, pts, multiplier, context):
    timeused = scrape_time_report(timelog)
    if timeused.internal_error:
        raise Exception("Unable to scrape runtime for efficiency comparison. Tell Julie! (%s)" % timeused.internal_error)

    if reject_regex is not None and re.match(reject_regex, output):
        return results.Inconclusive()

    execution_errors = summarize_execution(output, soln_output, exitcode)
    ratio = float(timeused.nsecs)/soln_time

    if execution_errors and ratio <= multiplier:  # time ok, but run was fishy, verify "good faith"
        if context in [testing.FOR_DRYRUN, testing.FOR_TESTSUITE]:  # if not for grading, score as 0, give summary of findings
            return results.Inconclusive(short="Time use (%s secs is %.1fx soln) %s" % (timeused.nsecs, ratio, execution_errors))
        if context == testing.FOR_PREGRADE:
            return results.Deferred()  # requires judgment, defer to interactive grader

        print "Submission uses: %s secs\nSolution uses:   %s secs" % (ui.blue(timeused.nsecs), soln_time)
        print ui.red("Time use ok (within %sx of solution), but run had execution errors that cast doubt on reliability of timing data." % multiplier)
        print ui.bold("Errors: ") + ui.blue(execution_errors)
        if "incorrect output" in execution_errors and ui.get_yes_or_no("Do you want to view the discrepancy in output?"):
            print results.summarize_mismatch(output, soln_output)
        options = [Option(1, "code seems complete and program executed in full", "time should be reliable"),
                   Option(0, "incomplete code and/or incomplete execution", "time is inconclusive")]
        (score, reason) = get_score_from_options("", "Should we trust the timing data from this run?", options)
        if score == 0:  # report is unreliable, result is inconclusive
            return results.Inconclusive()

    # from here, use scrape of time usage as truth
    if ratio <= multiplier:
        return results.Correct(score=pts, short="Passed, time on par with expectation")
    else:
        summary = "Time use %s secs is %.1fx soln " % (timeused.nsecs, ratio)
        if execution_errors is not None: summary += execution_errors
        return results.TooMuch(short=summary)

def score_requirement(test, output, deduction, failure_msg=None, deduct_msg=None):
    print "This submission has failed the automated test to %s." % test.description
    if failure_msg: print ui.red(failure_msg)
    elif output: print "Program output: %s" % ui.blue(output)
    print "Please review code to determine if requirement is met or not, automated test can be mistaken."
    if ui.get_yes_or_no("Does submission meet requirement?"):
        return results.Correct(score=test.totalpts, short="Accepted by grader as valid")
    else:
        while True:
            print "Suggested deduction for failing to meet this requirement is %s points. %s" % (ui.bold(str(deduction)), deduct_msg)
            # MC: I wanted to be able to give no deduction but say that they actually didn't meet the spec...
            deduct,comment = ui.get_number("Enter deduction to apply:", range(deduction+1), default=deduction, allow_comment=True)
            if deduct == deduction: break
            if ui.get_yes_or_no("Are you sure this situation warrants a deviation from standard deduction?"):
                while not comment:
                    comment = raw_input("Enter brief explanatory comment for student: ")
                break
        cls = results.Incorrect if deduct != 0 else results.Correct
        return cls(score=-deduct, short="Does not meet required specification" + (" (%s)" % comment if comment else ""))
