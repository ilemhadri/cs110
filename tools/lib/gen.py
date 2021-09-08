
"""
Julie Zelenski, 2010-present

The gen module has global variables and a few utility functions that are specific to the course tools package.
Utilities that are more general-purpose (i.e. not tied to course tools) live in the util module
"""

import commands, os, socket, sys
import util     # don't import other lib modules into gen -- keep its dependencies down!

def shortpath(path):
    """returns path shortened if possible (replace home with ~, discard coursepath)"""
    homedir = os.path.expanduser('~')
    # rewrite to canonical form of ir instead of ir.stanford.edu
    homedir = homedir.replace("/ir.stanford.edu/", "/ir/", 1)
    path = path.replace("/ir.stanford.edu/", "/ir/", 1)
    if path.startswith(homedir):
        return path.replace(homedir, "~", 1)
    prefix = os.path.commonprefix([path, COURSE_PATH+'/'])
    # don't shorten if only part in common is root slash
    return path.replace(prefix, '', 1) if len(prefix) > 1 else path

def is_instructor(user=None):
    if user is None: user = username()
    return (user == username() and (JZ_RUNNING or MC_RUNNING)) or user in INSTRUCTORS

def username():
    if "CT_USER" in os.environ: return os.environ["CT_USER"]   # JDZ temp hack for testing
    # should this use getpass.getuser() or whoami?
    status, output = commands.getstatusoutput("whoami")
    assert(status == 0), "cannot determine username (%s)" % output
    return output

def PLANTED():
    '''used for planting deliberate exceptions to test exception-handling'''
    import inspect
    (a, path,lineno,fnname,b, c) = inspect.stack()[1]  # read frame of caller
    filename = os.path.basename(path)
    (module, ext) = os.path.splitext(filename)
    fn = "%s.%s" % (module, fnname)
    if fn in PLANTED_ERRORS:
        raise Exception("PLANTED ERROR during %s, %s:%s" % (fnname, filename, lineno))

# Loading the gen module will read config variables from config.ini file and add
# those variables as module-level attributes with uppercase names. This provides
# easy, cheesy access for everyone by using gen.VARIABLE (excuse my use of global
# variables out of shameful laziness)
where_am_i = os.path.dirname(os.path.realpath(__file__))
CONFIG_PATH = os.path.normpath(where_am_i + "/../config/")
d = util.read_config(os.path.join(CONFIG_PATH, "gen.ini"))["gen"]
for key in d:  # add all keys from dict as attributes
    setattr(sys.modules[__name__], key.upper(), d[key])
JZ_RUNNING = username() in ["zelenski", "julie"]
MC_RUNNING = username() == "mchang91" or socket.gethostname().startswith("MChang")
NT_RUNNING = username() == "troccoli"
STAFF = TAS + INSTRUCTORS
#PLANTED_ERRORS = [testing.tests_for_assign", "base.render", "util.send_mail"]
PLANTED_ERRORS = []
