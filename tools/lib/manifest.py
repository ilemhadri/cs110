
"""
Julie Zelenski, 2017

"""

import copy, imp, os
import gen, testing, ui, util
from common import *
from masters import Master

def _manifest_paths(assignname, context, usemaster=False):
    if context == testing.FOR_SANITY:
        if usemaster:
            base = Master.master_for(assignname).path_for("samples")  # read from master staging area
        else:
            base = os.path.join(gen.COURSE_PATH, "samples", assignname)
        manifest = os.path.join(base, "SANITY.ini")
        pypath = os.path.join(base, "sanity.py")
    else:
        base = Master.master_for(assignname).path_for("grade")
        manifest = os.path.join(base, "GRADING.ini")
        pypath = os.path.join(base, "grading.py")
    return (manifest, pypath)

def _read_manifest_config(assignname, context, usemaster):
    """Returns config as read from manifest (INI file). will have loaded assign-specific python too"""
    (manifest, pypath) = _manifest_paths(assignname, context, usemaster)
    config = util.read_config(manifest, defaults={"filepath": os.path.dirname(manifest)})
    if os.path.exists(pypath):
        imp.load_source("testing", pypath)  # loads any assign-specifc python into the testing module
    return config

# TODO: JDZ filtering needs re-design (custom included not, xprefix on name, which context)
def tests_for_assign(assignname, context, filters=None, predicate=lambda t: not t.is_custom_template, usemaster=False):
    """return a list of Test objects by converting config read from manifest into Test objects"""
    sections = _read_manifest_config(assignname, context, usemaster)
    filtered = {}
    for testname in sections:
        # x prefix can be used to "comment-out" a test, still available to dryrun and runtests
        if context not in [testing.FOR_DRYRUN, testing.FOR_RUNTESTS] and testname.startswith('x'): continue
        filtered[testname] = sections[testname]

    tests = []
    for testname in sorted(filtered):   # each section represents one test
        d = dict(sections[testname])    # make dictionary out of this section
        d["name"] = testname            # store name of section as "name" field
        obj = testing.construct_test_from_dict(d)   # create Test object from dict of fields
        tests.append(obj)

    # if filters specified, winnow down to tests which match at least one filter
    if filters and len(filters):
        tests = [t for t in tests if any(pattern in t.name for pattern in filters)]
    # filter out interactive tests for dryrun
    if context == testing.FOR_DRYRUN:
        tests = [t for t in tests if not t.is_interactive]
    if predicate:
        tests = [t for t in tests if predicate(t)]

    for t in tests:
        t.validate()   # validate each test that made it through all the filters
    return tests

def sanity_check_exists(assignname):
    """return True/False by looking for sanity manifest in samples for this assignment"""
    (manifest, pypath) = _manifest_paths(assignname, testing.FOR_SANITY)
    return os.path.exists(manifest)

def custom_template(reponame, usemaster=False):
    # return Custom template if it exists in sanity manifest, otherwise returns None
    options = tests_for_assign(reponame, testing.FOR_SANITY, predicate=lambda t: t.is_custom_template, usemaster=usemaster)
    asserts.manifest(len(options) <= 1, "Sanity check for %s has two or more custom test templates %s, required to be unique" % (reponame, ui.pretty_list(options)))
    return options[0] if len(options) else None

def create_custom_sanity_test(template, line, linenum):
    """build test off Custom template, with raise if invalid"""
    t = copy.deepcopy(template)
    return t.init_from_string(line, linenum)

def read_and_validate(reponame):
    # TODO JDZ: where to trap case where manifest not exist in read
    if sanity_check_exists(reponame):
        sanity_tests = tests_for_assign(reponame, testing.FOR_SANITY)
        custom_sanity = custom_template(reponame)
    else:
        sanity_tests = []
        custom_sanity = None
    grading_tests = tests_for_assign(reponame, testing.FOR_TESTSUITE)

    found = [t for t in grading_tests if isinstance(t, testing.GraderReview)]
    asserts.manifest(len(found) <= 1, "Grading manifest has two or more grader review tests %s, required to be unique" % ui.pretty_list(found))
    wr = found[0].review_template() if len(found) == 1 else None
    return (sanity_tests, custom_sanity, grading_tests, wr)

def sanity_tests(reponame, usemaster=False):
    return tests_for_assign(reponame, testing.FOR_SANITY, usemaster=usemaster)

def run_sanity_check(path, reponame, tests=None, noisy=True, usemaster=False):
    """Runs all assignment sanity tests on submission and returns tuple (nfailures, ntests)"""
    if not tests:  # no custom tests specified, use tests from standard sanity check and exclude any Custom test if present
        tests = [t for t in sanity_tests(reponame, usemaster)]
    nfailures = 0
    sanity_results = {}
    for test in tests:
        result = test.run(path, testing.FOR_SANITY, noisy)
        sanity_results[test.name] = result
        if not result.passed(): nfailures += 1
    return (nfailures, len(tests))
