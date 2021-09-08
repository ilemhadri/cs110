
"""
Julie Zelenski, 2009-present
Ryan Noon, original design

The grading module manages the process of grading a single submission.
Mostly this list just a loop to iterate over each test, using the testing module to
execute test and score outcome, then updates grade report. A Submission object manages
the grade report (stored as GCACHE).
The two grading modes are:
     pregrade (updates all non-interactive test, writes GCACHE)
     autograde (updates all tests, writes GCACHE, handles irregularities, completes grade report)
"""

import os
import course, testing, ui, util

def grader_note(repo):
    contents = util.read_file(os.path.join(repo.path, "NOTE_TO_GRADER")).strip()
    return "%s\n%s\n%s" % ("-"*20, ui.blue(contents), "-"*20) if contents else "<empty>"

def handle_irregularities(repo):
    print ui.bold("Before you finish with this one... Remember submission has a NOTE_TO_GRADER that says:\n") + grader_note(repo)
    choices = ["leave everything as is", "set late day count", "apply adjustment to total score"]
    answer = ui.get_lettered_choice(choices)
    if answer == 0:
        return
    elif answer == 1:
        print "\nSubmitted %s" % ui.blue(ui.nicedatetime(repo.sub.subdate)),
        due = course.duedate_for(repo.reponame)[0]
        print "Assignment was due %s" % ui.blue(ui.nicedate(due))
        print "Current late days = %d" % repo.sub.numlate
        repo.sub.numlate = ui.get_number("Enter count of late days to record for this submission:", range(0, 5))
        repo.sub.commit_changes()
    elif answer == 2:
        print "\nCurrent total point score is %s" % repo.sub.points_string()
        (earned, max) = repo.sub.points_tuple()
        amt = ui.get_number("Enter change in point total (negative or positive, 0 to cancel/remove):", range(-earned, 100+max-earned+1))
        reason = raw_input("Enter reason for change (this comment will be shown to student): ").strip() if amt != 0 else ''
        repo.sub.adjust_total(amt, reason)
        print "New total point score is %s" % repo.sub.points_string()

def verify_repo_ready_for_grading(repo, has_grader_note, confirm):
    """checks status of repo to ensure head/submit coherent. Complains if something seems out of whack"""
    issues = repo.grading_concerns()
    if issues:
        print ui.red("No bueno: " + issues)
        if confirm:
            if has_grader_note:
                print "The submission has a NOTE_TO_GRADER which is supposed to explaisn how to handle it:"
                print grader_note(repo)
                if not ui.get_yes_or_no("Continue with grading? If unsure, type n to skip", default="n"):
                    return False
            else:
                print "Skipping %s" % repo.id
                print "Find out what's up, explain in NOTE_TO_GRADER file, then re-run autograder"
                return False
    elif has_grader_note:
        print "This submission has a NOTE_TO_GRADER which says:\n" + grader_note(repo)
        raw_input("Hit return to continue")
    return True

def autograde(repo, tests_to_run, update=False):
    """Entry point to grade a submission for context autograde"""
    repo.start_grading()
    has_grader_note = os.path.exists(os.path.join(repo.path, "NOTE_TO_GRADER"))
    if not verify_repo_ready_for_grading(repo, has_grader_note, confirm=True):
        return None
    for t in tests_to_run:
        previous = repo.sub.cached_result_for(t)
        # check for previous valid results if not updating
        if not update and previous and not previous.deferred():
            print "  PREGRADED %-25.25s %s" % (t.name, previous.string_for_grader())
            continue  # don't re-run test, previous result is good to use
        result = t.run(repo.path, testing.FOR_AUTOGRADER, repo=repo)
        if update and previous and result != previous:
            print ui.bold("Updated"), "(previously %s)" % previous.string_for_grader()
        repo.sub.save_test_result(t.name, result)
    if not update: repo.sub.mark_finished()
    print "\nAutograde total for %s = %s\n" % (ui.bold(repo.id), ui.blue(repo.sub.summary_string()))
    if has_grader_note: handle_irregularities(repo)
    return repo

def pregrade(repo, tests_to_run, update=False):
    """Entry point to grade a submission for context pregrade"""
    repo.start_grading()
    verify_repo_ready_for_grading(repo, False, confirm=False)
    orig = repo.sub.points_string()

    for t in tests_to_run:
        previous = repo.sub.cached_result_for(t)
        if not update and previous: continue  # skip any test previously run if not updating
        ui.overprint("Testing %s on %-25.25s" % (repo.id, t.name))
        result = t.run(repo.path, testing.FOR_PREGRADE, repo=repo)
        repo.sub.save_test_result(t.name, result)
        if update and previous and result != previous:
            print ui.bold("Updated"), "(was %s now %s)" % (previous.string_for_grader(), result.string_for_grader())
        elif not result.passed(): print result.string_for_grader()
    ui.overprint('')
    print "Pregrade total for %s = %s (%s)\n" % (ui.bold(repo.id), ui.blue(repo.sub.points_string()), orig)
    return repo

