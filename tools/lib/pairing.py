
"""
Julie Zelenski, 2013-present

Little module that reads/writes the pairings.ini file (and includes caching so not repeatedly read/coerce)
"""

import ConfigParser
import collections, os, random
import gen, util

class Pairing(object):
    """This object represents the pairings (ta/tags) for an assignment's worth of student submissions."""
    CACHE = {}
    PAIRING_PATH = os.path.join(gen.PRIVATE_DATA_PATH, "pairings")

    def __init__(self, assignname):
        self.assignname = assignname
        self.bysunet = collections.defaultdict(lambda: util.Struct(ta=None, tags=[]))
        self.cur_load = collections.defaultdict(int)

        (sections, pe) = self.read_pairing_file(assignname)
        # file is organized as map from [tag/ta] to sunets
        # create parallel structure mapping from sunet to tag for ease of lookup
        if "ta" in sections:
            for ta in sections["ta"]:
                self.cur_load[ta] = len(sections["ta"][ta])
                for sunet in sections["ta"][ta]:
                    if sunet in self.bysunet:  # previously seen TA was paired to this sunet
                        pe.append(-1, "%s paired to both %s and %s" % (sunet, self.bysunet[sunet].ta, ta))
                    self.bysunet[sunet].ta = ta
        if "tagged" in sections:
            for tag in sections["tagged"]:
                for sunet in sections["tagged"][tag]:
                    self.bysunet[sunet].tags.append(tag)
        if len(pe.errors) > 0: raise pe  # raise collected parse errors

    def write_pairing_file(self):
        byta = collections.defaultdict(list)
        bytag = collections.defaultdict(list)
        for sunet in self.bysunet:
            if self.bysunet[sunet].ta: byta[self.bysunet[sunet].ta].append(sunet)
            for tag in self.bysunet[sunet].tags: bytag[tag].append(sunet)
        path = os.path.join(self.PAIRING_PATH, "%s.ini" % self.assignname)
        config = ConfigParser.SafeConfigParser()
        config.add_section("ta")
        for key in sorted(byta):
            config.set("ta", key, '[' + ", ".join(sorted(byta[key])) + ']')
        config.add_section("tagged")
        for key in sorted(bytag):
            config.set("tagged", key, '[' + ", ".join(sorted(bytag[key])) + ']')
        with open(path, "wb") as f:
            config.write(f)
        return path

    @classmethod
    def read_pairing_file(cls, fname):
        """returns tuple (sections, ParsingError). Caller can append issues to ParsingError and raise it
        if further analysis finds structural invalidity in file contents"""
        path = os.path.join(cls.PAIRING_PATH, "%s.ini" % fname)
        pe = ConfigParser.ParsingError(path)
        if not os.path.exists(path): return ({}, pe)  # returns empty dict if no pairing yet exists
        return (util.read_config(path), pe)

    @classmethod
    def read_pairing_config(cls):
        avoid = collections.defaultdict(list)  # return empty list if key not set
        load_fractions = collections.defaultdict(lambda: 1)  # return 1 for all keys unless explicity set
        (sections, pe) = cls.read_pairing_file("config")
        if "avoid" in sections:
            avoid.update(sections["avoid"])
        if "adjustments" in sections:
            for (ta, percent) in sections["adjustments"].items():  # verify validity of entries in load adjustment list
                if ta.startswith('_'): continue
                if ta not in gen.STAFF: pe.append(-1, "unexpected adjustment for '%s' (not known at TA)" % ta)
                # MC: Allow > 1 to give extra grading to compensate for e.g. exam grading
                if not (isinstance(percent,int) or isinstance(percent,float)) or percent < 0: pe.append(-1, "%s given invalid adjustment '%s'" % (ta, percent))
            load_fractions.update(sections["adjustments"])
        if len(pe.errors) > 0: raise pe  # raise collected parse errors
        return (avoid, load_fractions)

    def ta_for_sunet(self, sunet):
        return self.bysunet[sunet].ta

    def tags_for_sunet(self, sunet):
        return self.bysunet[sunet].tags

    def sunets_for_tag(self, tag):
        return [s for s in self.bysunet if tag in self.bysunet[s].tags]

    def pair_sunet(self, sunet, ta=None):
        """If TA given, will pair as requested, otherwise will randomly choose one of TAs
        with lightest load to make pairing. Respects avoid setting"""
        if ta is None:
            # wait to load config until really needed (making new random pairing)
            if not hasattr(self, "avoid"):
                (self.avoid, self.load_fractions) = self.read_pairing_config()
            eligible_graders = [t for t in gen.TAS if self.load_fractions[t] != 0 and sunet not in self.avoid[t]]
            calc_load = lambda ta: self.cur_load[ta]*(1.0/self.load_fractions[ta])  # computes ta's load scaled by adjustment
            minload = min([calc_load(t) for t in eligible_graders])  # get min load across all eligible
            chosen_ta = random.choice([t for t in eligible_graders if calc_load(t) == minload])  # choose from eligible at min load
        else:
            chosen_ta = ta
        self.bysunet[sunet].ta = chosen_ta
        self.cur_load[chosen_ta] += 1
        return chosen_ta

    def tag_sunet(self, sunet, tag):
        if tag not in self.bysunet[sunet].tags:  # don't add to same tag more than once (tidiness)
            self.bysunet[sunet].tags.append(tag)

    def count_tag(self, tag):
        return sum([1 if tag in v.tags else 0 for v in self.bysunet.values()])

    @classmethod
    def for_assign(cls, assignname):
        """factory method to get Pairing obj for assignname, uses cache to share one Pairing per-assign"""
        if assignname not in cls.CACHE:
            cls.CACHE[assignname] = cls(assignname)
        return cls.CACHE[assignname]
