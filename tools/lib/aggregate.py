
"""
Julie Zelenski, 2016-present

Table of test/sunet results, used by dryrun
Read/write to pickled cache file
Goal is fairly simple, but code is decidedly unpleasing as currently written, ugh
"""

import collections, cPickle, os
import gen, results, ui, util


# TODO: JDZ: is this the right way to handle this?
class Missing(results.Result):
    onechar = '@'; short = "Missing from dryrun cache"; score = '---'

# overview:
# dryrun cache file is a pickled dict
# cache[TIPS][sunet] = tip revision
# cache[testname][sunet] = result of running test on sunet's repo
# testname is string from manifest

TIPS = "_TIPS"
class Aggregate(object):
    """This object represents summary of test results for an assignment's worth of student submissions."""

    def __init__(self, cachename=None):
        self.path = os.path.join(gen.PRIVATE_DATA_PATH, "dryrun", cachename) if cachename else None
        self.all_results = collections.defaultdict(dict)  # dict organized [testname][sunet] = result
        self.updated = []  # queue of tuple(testname, sunet, result) to be added to cache
        self.tips = {}  # dict organized [sunet] = tip revision

    def read_cache(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r") as fp:
                    return cPickle.load(fp)
        except Exception:
            print ui.red("failed to read pickle file %s, moving aside." % self.path)
            util.archive_file(self.path)
        return {}

    def write_cache(self, dict_to_save):
        util.system("mkdir -p %s" % os.path.dirname(self.path))
        with open(self.path, "w") as fp:
            cPickle.dump(dict_to_save, fp)

    def commit_updates(self):
        pickled = self.read_cache()
        for (testname, sunet, result) in self.updated:
            if testname not in pickled: pickled[testname] = {}
            if result.__class__ == results.NoExecute: continue
            pickled[testname][sunet] = result
        self.write_cache(pickled)
        self.updated = []  # reset queue to empty

    def num_updates(self):
        return len(self.updated)

    def update_result(self, testname, sunet, result, tiprev):
        # merge with current results, queue update for later write
        self.updated.append((testname, sunet, result))
        if sunet not in self.tips: self.updated.append((TIPS, sunet, tiprev))   # cheezy
        self.all_results[testname][sunet] = result

    def cached_result_for(self, testname, sunet):
        return self.all_results[testname].get(sunet, None)

    def find_and_remove_stale(self, tnames_in_manifest, repos):
        pickled = self.read_cache()
        stale_tests = [t for t in pickled if t != TIPS and t not in tnames_in_manifest]
        for t in stale_tests:
            del pickled[t]
        tips = pickled.get(TIPS, {})  # use empty dict if no tip revisions cached
        stale_sunets = set(r.sunet for r in repos if r.sunet in tips and tips[r.sunet] != r.grading_head)
        for (tname, tsunets) in pickled.items():
            for s in (stale_sunets & tsunets.viewkeys()):  # intersect stale with cached
                del tsunets[s]
        self.write_cache(pickled)
        return (stale_tests, stale_sunets)

    def select_from_cache(self, tests, repos):
        '''loads table with test/sunet results read from cache'''
        self.all_results = collections.defaultdict(dict)
        pickled = self.read_cache()
        self.tips = pickled.get(TIPS, {})  # save tips, keep separate from dict of results
        sunets_to_extract = set(r.sunet for r in repos)
        for t in tests:
            cached_for_test = pickled.get(t.name, {})  # use empty dict if no cache entry for test
            # find intersection between selected sunets and those sunets with cached result for this test
            found_sunets = set(sunets_to_extract & cached_for_test.viewkeys())
            if found_sunets: self.all_results[t.name] = dict((s, cached_for_test[s]) for s in found_sunets)

    def summarize_one_sunet(self, sunet, testnames):
        row_results = [self.all_results[tname][sunet] if sunet in self.all_results[tname] else Missing() for tname in testnames]
        passed_all = all(r.did_pass for r in row_results)
        (score, possible) = results.sum_points(row_results)
        return util.Struct(sunet=sunet, perfect=passed_all, score=score, possible=possible, results=row_results)

    def organize_by_sunet(self, consolidate_perfect=True):
        columns = sorted(self.all_results.keys())
        rows = []
        perfect_row = None
        nperfect = 0
        # include a row for each sunet in any test result in table
        for s in set(s for val in self.all_results.values() for s in val):
            row = self.summarize_one_sunet(s, columns)
            if not row.perfect or not consolidate_perfect:
                rows.append(row)
            else:  # perfect sunets consolidated into one row
                if not perfect_row:
                    perfect_row = row
                    rows.append(perfect_row)
                nperfect += 1
                perfect_row.sunet = "PERFECT (%d)" % nperfect
        return util.Struct(rows=rows, cols=columns)

    def summarize_one_test(self, testname, classes=[]):
        row_results = self.all_results[testname].values()
        by_class = collections.Counter([r.__class__ for r in row_results])
        # convert count from int to string here for so later can do right thing
        counts = [str(by_class[cls]) if by_class[cls] else '' for cls in classes]
        return util.Struct(testname=testname, counts=counts, nfailed=sum(not result.passed() for result in row_results), ntotal=len(row_results))

    def organize_by_test(self):
        # figure out which result classes to use as column headers (winnow to only needed, not all)
        # gather result classes for every entry, push through set to unique
        used = set(result.__class__ for val in self.all_results.values() for (sunet, result) in val.items())
        # table column order is dictated by order of class declaration (cheezy)...
        classes = [cls for cls in results.Result.__subclasses__() if cls in used]
        rows = [self.summarize_one_test(tname, classes) for tname in sorted(self.all_results.keys())]
        return util.Struct(rows=rows, cols=[cls.__name__ for cls in classes])
