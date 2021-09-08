
"""
Julie Zelenski, 2016-present

New module added to gather data/operations that are course-specific
(registration, assign/lab info, website/filesystem organization)
This info has previously been scattered about gen, util, config files, etc.
Intent is to consolidate here.
"""

import datetime, gen, os, ui, util
from common import *

ASSIGN_INFO = None
LAB_INFO = None

def has_public_page(reponame):
    # change strategy as of 15-3 to use existence of web page rather than repo created
    return os.path.exists(os.path.join(gen.COURSE_PATH, "WWW", reponame, "index.html"))

def published_labs():
    return [(labname, "") for labname in ["lab%d" % num for num in range(1, 10)] if has_public_page(labname)]

def published_assigns():
    return [(assignname, assign_info(assignname).name) for assignname in assign_names() if has_public_page(assignname)]

def read_classlist(include_htaccess=True, include_extras=True):
    """Gets sunets from htaccess file in WWW/restricted which is updated nightly to match axess
    then combine with entries from extra sunets file"""
    registered = []
    extras = []
    htaccess_path = os.path.join(gen.COURSE_PATH, "WWW/restricted/.htaccess")
    extra_path = os.path.join(gen.PRIVATE_DATA_PATH, "extra_sunets.txt")

    if include_htaccess and os.path.exists(htaccess_path):
        registered = util.grep_file("require user (\w+)", htaccess_path)
    if include_extras and os.path.exists(extra_path):
        extras = util.grep_file("(\w+)", extra_path)
    return util.without_duplicates(registered + extras)

def add_to_classlist(sunet):
    util.append_to_file(sunet + '\n', os.path.join(gen.PRIVATE_DATA_PATH, "extra_sunets.txt"))

def duedate_for(assignname):
    """returns tuple(duedate, endgrace), if missing/malformed, raises Exception"""
    info = assign_info(assignname)
    if info.gracehours == 0:
        endgrace = None
    else:
        endgrace = info.duedate + datetime.timedelta(hours=info.gracehours)
    return (info.duedate, endgrace)

def compute_late_days(assignname, submitdate, spare_minutes=10):
    """counts number of days late (will be 0 if ontime/early)"""
    due = duedate_for(assignname)[0]
    amt_late = submitdate - due - datetime.timedelta(minutes=spare_minutes)
    if amt_late.total_seconds() <= 0:
        nlate = 0
    else:
        nlate = 1 + amt_late.days
    return nlate

ON_TIME, IN_GRACE, TOO_LATE = range(3)

def check_submit_lateness(assignname, submitdate):
    (due, endgrace) = duedate_for(assignname)
    submitdate -= datetime.timedelta(minutes=1)  # one minute of slop in whether counted as on-time/within grace
    if submitdate <= due: return ON_TIME
    elif endgrace and submitdate <= endgrace: return IN_GRACE
    else: return TOO_LATE

def ontime_bonus(assignname):
    # ontime bonus requires grace period available to be active, otherwise disabled
    endgrace = duedate_for(assignname)[1]
    if not endgrace:
        return 0
    else:
        return float(assign_info(assignname).ontimebonus)

def late_policy(submitname):
    return assign_info(submitname).latepolicy

def url_gradebook():
    return "%s/cgi-bin/gradebook" % gen.COURSE_URL

def url_review(assignname, sunet=None):
    return "%s/cgi-bin/%s" % (gen.COURSE_URL, assignname) + ("/%s" % sunet if sunet else "")

def url_doc(pagename):
    return "%s/%s" % (gen.COURSE_URL, pagename)

def _validate_lab_info(info):
    for (labkey, val) in sorted(info.laboptions.items()):
        fields = set(val.__dict__.keys())
        missing = {"name", "capacity", "location", "ta", "password"} - fields  # required fields that are missing
        asserts.config(len(missing) == 0, "lab config for %s missing required fields %s" % (labkey, list(missing)))
        asserts.config(isinstance(val.capacity, int), "lab config for %s has invalid capacity %s" % (labkey, val.capacity))
    names = [l.name for l in info.laboptions.values()]
    duplicates = [n for n in names if names.count(n) > 1]
    # find duplicate display names
    asserts.config(len(duplicates) == 0, "lab config has duplicate lab names %s, need to disambiguate" % ui.pretty_list(duplicates))
    fields = set(info.__dict__.keys())
    missing = {"signups_open", "labs_start", "num_days_open", "skip_weeks"} - fields   # required fields that are missing
    asserts.config(len(missing) == 0, "lab config [main] missing required fields %s" % (list(missing)))
    asserts.config(isinstance(info.signups_open, datetime.datetime), "lab config [main] has invalid signups_open '%s'" % info.signups_open)
    asserts.config(isinstance(info.labs_start, datetime.datetime), "lab config [main] has invalid labs_start '%s'" % info.labs_start)
    asserts.config(isinstance(info.num_days_open, int) and info.num_days_open > 0, "lab config [main] has invalid num_days_open '%s'" % info.num_days_open)

def read_lab_config(optional=False):
    """Read lab_info config file, validate internal consistency, assert/raise on issues"""
    global LAB_INFO
    if LAB_INFO is not None: return LAB_INFO
    path = os.path.join(gen.PRIVATE_DATA_PATH, "lab_info.ini")
    if not os.path.exists(path) and optional: return None
    config = util.read_config(path)
    asserts.config("main" in config, "lab config missing required section [main]")
    s = util.Struct(**config["main"])
    s.laboptions = {}  # keys are the original section name 04-Wed 10:30 (so can sort)
    for section_name in set(config.keys()) - {"main"}:
        name_parts = section_name.split("-", 1)
        asserts.config(len(name_parts) == 2, "lab section '%s' is not in the expected form SortKey-Name" % section_name)
        this_lab = util.Struct(**config[section_name])
        this_lab.name = name_parts[1].strip()
        s.laboptions[section_name] = this_lab
    _validate_lab_info(s)
    # calculate lab open-close dates here (avoids messy code later)
    s.labdates = {}
    # set open at midnight, close at 23:59 of nth day
    lab1_open = s.labs_start.replace(hour=0, minute=0)
    lab1_close = lab1_open + datetime.timedelta(days=s.num_days_open, minutes=-1)
    for n in range(1, 10):
        # labN is n-1 weeks after lab1, but also need to account for skipped
        nweeks = n - 1 + sum(1 for i in s.skip_weeks if n >= i)
        offset = datetime.timedelta(days=7*nweeks)
        s.labdates["lab%d" % n] = util.Struct(open=lab1_open + offset, close=lab1_close + offset)
    LAB_INFO = s
    return s

def lab_info(labname):
    """validate happens in read"""
    read_lab_config()
    return LAB_INFO.labdates[labname] if labname in LAB_INFO.labdates else None

def _read_assign_config():
    """Read assign_info config file, no validation"""
    global ASSIGN_INFO
    if ASSIGN_INFO is None:
        config = util.read_config(os.path.join(gen.CONFIG_PATH, "assign_info.ini"))
        ASSIGN_INFO = dict((name, util.Struct(**(config[name]))) for name in config)

def _validate_assign(name, info):
    fields = set(info.__dict__.keys())
    deprecated = {"maxlate"} & fields
    asserts.config(len(deprecated) == 0, "assign config for %s has deprecated fields %s" % (name, list(deprecated)))
    missing = {"name", "duedate", "ontimebonus", "latepolicy", "gracehours"} - fields
    asserts.config(len(missing) == 0, "assign config for %s missing required fields %s" % (name, list(missing)))
    asserts.config(isinstance(info.duedate, datetime.datetime), "assign config for %s has invalid duedate '%s'" % (name, info.duedate))
    asserts.config(isinstance(info.gracehours, int) and info.gracehours >= 0, "assign config for %s has invalid grace period %s" % (name, info.gracehours))
    asserts.config(info.latepolicy in ["cap", "grace"], "assign config for %s has invalid late policy '%s' (expected grace or cap)" % (name, info.latepolicy))

def assign_names():
    _read_assign_config()
    return sorted(ASSIGN_INFO.keys())

def assign_info(reponame):
    """validates whatever entry is being returned"""
    if reponame in assign_names():
        info = ASSIGN_INFO[reponame]
        _validate_assign(reponame, info)
        return info
    return None

def quarter_id():
    # returns Stanford internal quarter id, e.g. 1176 for 2017-8 spring quarter
    (year, term) = util.match_regex("(\d\d)-(\d)$", str(gen.QUARTER), 1, 2)
    asserts.config(year and term, "gen config quarter '%s' not in correct year-term form e.g. 16-2" % gen.QUARTER)
    return "1%s%s" % (int(year) + 1, int(term) * 2)

def cgi_user():
    # JDZ perhaps course should someday act like Repo (get atttribute on demand)
    if hasattr(gen, "CGI_USER"): return gen.CGI_USER
    u = "class-%s-%s.cgi" % (gen.COURSE.lower(), quarter_id())
    setattr(gen, "CGI_USER", u)
    return u

def staff_afs_group():
    if hasattr(gen, "STAFF_AFS_GROUP"): return gen.STAFF_AFS_GROUP
    g = "%s-%s-admins" % (quarter_id(), gen.COURSE.lower())
    setattr(gen, "STAFF_AFS_GROUP", g)
    return g

def public_repo_path():
    return os.path.join(gen.COURSE_PATH, "repos")

def master_repo_path(reponame):
    return os.path.join(gen.COURSE_PATH, "staff", "master_repos", reponame)

