
"""
Julie Zelenski, 2014-present

The util module defines features that have general-purpose use.
(many of the functions were originally defined in gen)
Avoid imports of other modules, esp. not gen (because gen imports util)
"""

import commands, ConfigParser, datetime, errno, getopt, operator, os, re, shutil, smtplib, sys, tempfile, termios, time
from common import *

class Struct(object):
    """Ideally would do this with namedtuple, but our version of python is too old.
    So make our own mock struct-like thing.  Create using s = Struct(field1=val, field2=val),
    can access fields as s.field1 """
    def __init__(self, **kwds):
        self.__dict__.update(**kwds)

    def update(self, **kwds):
        self.__dict__.update(**kwds)
        return self

    def __repr__(self):
        args = ["%s=%s" % (k, repr(v)) for (k, v) in sorted(vars(self).items())]
        return "Struct(%s)" % ", ".join(args)

    def __str__(self):
        args = ["%s = %s" % (k, str(v)) for (k, v) in sorted(vars(self).items())]
        return '\n'.join(args) + '\n'

def unique_match(pattern_str, choices, cmp=operator.contains):
    """looks for a pattern_str in a list of choices (each choice converted to str for cmp)
     default cmp allows substring match, use operator.eq for equality or str.startswith for prefix match"""
    if pattern_str in choices: return pattern_str  # exact match, return that one without looking further
    matches = [c for c in choices if cmp(str(c), pattern_str)]  # gather matches (prefix/substr/etc)
    return matches[0] if len(matches) == 1 else None  # return if unique

def match_regex(pattern, text, *groups):
    """Minor convenience wrapper around re.search. Optional arg groups allows you to
    indicate which capturing group(s) to return (as tuple or singleton). If no groups, default to
    returns group(1) (if there was a group(1)) otherwise group(0)"""
    singleton = (not groups or len(groups) == 1)
    match = re.search(pattern, text)
    if not match: return None if singleton else tuple(None for i in range(len(groups)))
    if singleton:
        default = 1 if match.lastindex >= 1 else 0
        return match.group(groups[0] if groups else default)
    return tuple(match.group(g) for g in groups)

def grep_text(pattern, text, *groups):
    """Applies pattern line-by-line to text, returns list of matches.
    If no groups specified and no capturing group in pattern, result contains
    each matching line in its entirety. If no groups specified and yes capturing
    group in pattern, result contains group(1) from each matching line.
    If groups specified, returns tuple of those groups from each matching line.
    If you want result to contain matching pattern in entirety (but not full line),
    ask for group 0 or enclose entire pattern in () to become group(1)"""
    results = []
    for line in text.split("\n"):
        matched = re.search(pattern, line)
        if matched:
            if groups or matched.lastindex >= 1:
                results.append(match_regex(pattern, line, *groups))
            else:
                results.append(line)
    return results

def grep_file(pattern, path, *groups):
    """Open file, pass contents to grep_text. Raises exception if file can't be opened (no exist)
    Return list of matches (see grep_text) for more info on what each match item is"""
    with open(path) as f:
        results = grep_text(pattern, f.read(), *groups)
    return results

def flatten(list_of_lists):
    return sum(list_of_lists, [])

def without_duplicates(seq, key=None):
    """"This operation is order-preserving. The returned sequence retains first occurrence of any
    duplicates, discards subsequent. The function key(item) used to extract unique-id from item,
    if None, uses identity fn"""
    seen = {}
    result = []
    for item in seq:
        uniqid = key(item) if key else item
        if uniqid in seen: continue
        seen[uniqid] = True
        result.append(item)
    return result

# JDZ: I need to clean this design up
def system(cmd, echo=False, exit=True, quiet=False):
    import ui
    if echo: print ui.faint(cmd)
    status, output = commands.getstatusoutput(cmd)
    if echo: print ui.faint(output)
    if status == 0 and not quiet:
        return output
    elif status == 0 and quiet:
        return None
    elif status != 0 and exit:  # had non-zero status
        error_output = ui.abbreviate(output, maxlines=80).strip()
        raise Exception("command '%s' exited with non-zero status (%s)" % (cmd, error_output))
    elif status != 0 and quiet:
        return output
    else:
        return None

def system_echo(cmd, exit=True):
    """echo version prints cmd+output during operation"""
    return system(cmd, echo=True, exit=exit)

def system_quiet(cmd):
    return system(cmd, echo=False, exit=False, quiet=True)

def is_single_line(str):
    # 120 is good length for what fits on terminal
    return '\n' not in str[:-1] and len(str) <= 120

def is_int(val):
    try:
        int(val)
        return True
    except ValueError:
        return False

def stty_onclr(fd):
    # below is python equivalent of stty -onclr to disable translate of LF to CRLF
    attr = termios.tcgetattr(fd)
    attr[1] = attr[1] & ~termios.ONLCR  # attr[1] is oflag
    termios.tcsetattr(fd, termios.TCSANOW, attr)

def unbuffer_stdout():
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

def special_read(fd, truncate_len):
    '''Used only in execute_command to read the pipe with command results.
    Has some special quirks/conveniences for this specific situation.
    1) read and discard all content after hitting truncate_len
    2) EOF usually signaled by read returning empty but if reading from tty, treat OSError as EOF
       (necessary for linux version of pty)
    3) remove trailing newline from output'''
    buf = ''
    did_discard = False
    while True:
        try:
            cur = os.read(fd, 1024)  # use os.read (less buggy than python File)
            if cur == "": break   # EOF returns empty (expected behavior)
            if len(buf) < truncate_len:
                buf += cur
            else:
                did_discard = True
        except OSError:
            if os.isatty(fd): break  # EOF for pty raises error, swallow it (http://bugs.python.org/issue5380)
            raise                 # otherwise re-raise actual error
    os.close(fd)
    if did_discard: buf = buf[:truncate_len] + "..."
    if buf and buf[-1] == '\n': buf = buf[:-1]  # ugh, remove trailing newline if present
    return buf

def samefile(p1, p2):
    # os.path.samefile raises exception if either path doesn't exist, this version returns False
    return os.path.exists(p1) and os.path.exists(p2) and os.path.samefile(p1, p2)

def remove_files(*paths):
    """one or more file paths to remove, suppress error raised if a path doesn't exist"""
    for p in paths:
        try:
            os.remove(p)
        except OSError as ex:
            if ex.errno == errno.ENOENT:
                pass
            else:
                raise

def force_remove_dir(path):
    if os.path.exists(path):
        # first, give user all permissions (repos created no wd for us, but keep a, so can change here)
        import gen
        system("find %s -type d -print0 | xargs -0 -n 1 -I FNAME fs sa FNAME %s all" % (path, gen.username()))
        shutil.rmtree(path)

def read_file(path):
    if not os.access(path, os.R_OK) or os.path.isdir(path): return None
    with open(path, 'r') as fp:
        contents = fp.read()
    return contents

def write_file(contents, path, makeparent=False):
    if makeparent:
        system("mkdir -p %s" % os.path.dirname(path))
    with open(path, 'w') as fp:
        fp.write(contents)

def append_to_file(contents, path, makeparent=False):
    if makeparent:
        system("mkdir -p %s" % os.path.dirname(path))
    with open(path, 'a+') as fp:
        fp.write(contents)

def archive_file(path):
    """given path like /a/b/NAME, will rename to /a/b/NAME_# using first unused suffix number"""
    if not os.access(path, os.W_OK):
        return
    i = 1
    renamed_path = None
    while True:
        if not os.access("%s_%d" % (path, i), os.F_OK):
            renamed_path = "%s_%d" % (path, i)
            break
        i += 1
    os.rename(path, renamed_path)
    if os.access(path+'~', os.F_OK):
        os.remove(path+'~')
    return renamed_path

def convert_line_endings(path):
    with open(path, "rU") as orig:  # U will cause newlines to be converted
        data = orig.read()
    with open(path, "w") as converted:
        converted.write(data)

def coerce_primitive(str):
    """given a string, attempts to recognize it as a primitive type and coerce as such. 
    Tries formats below in order until one is recognized:
        None (as literal)
        boolean expressed True/False
        integer
        float
        date expressed month/day/year
        original string
    """
    val = str.strip()
    asserts.parser(val != "", "value is empty")

    if val == "None": return None

    if val == "True": return True
    if val == "False": return False

    try: return int(val)
    except ValueError: pass

    try: return float(val)
    except ValueError: pass

    # JDZ reconsider!
    # two diff formats allow date with or without time, if no time, datetime will default to midnight
    # I think we are currently using both formats in our ini files, but this does not seem
    # desirable -- missing time could be accidental and needs to be reported to draw attention
    allowed_fmts = ["%m/%d/%Y %H:%M", "%m/%d/%Y"]
    for fmt in allowed_fmts:
        try: return datetime.datetime(*(time.strptime(val, fmt)[0:6]))
        except ValueError: pass

    asserts.parser(not val.startswith('['), "nested list")
    asserts.parser(not val.startswith('{'), "nested dict")

    return val

def coerce_dict_item(str):
    asserts.parser(":" in str, "invalid dict item")
    (key_str, val_str) = str.split(':', 1)
    return (coerce_primitive(key_str), coerce_primitive(val_str))

def coerce_to_type(str):
    val = str.strip()
    if val.startswith('['):
        asserts.parser(val.endswith(']'), "unterminated list")
        return [coerce_primitive(x) for x in val[1:-1].split(',') if x is not ""]
    elif val.startswith('{'):
        asserts.parser(val.endswith('}'), "unterminated dict")
        return dict((coerce_dict_item(x) for x in val[1:-1].split(',') if x is not ""))
    else:
        return coerce_primitive(val)

def read_config(path, defaults=None):
    """given a path, will use a SafeConfigParser to read file, then post-processes items to recognize type of
    values and coerce from string to proper type. Used for parsing course info file, assignment info file,
    pairing files, testing manifest, etc. Optional defaults argument is a dict containing default values"""
    converted = {}
    scp = ConfigParser.SafeConfigParser(defaults, allow_no_value=False)  # JDZ when in python3, add strict=True to report duplicate sections
    scp.readfp(open(path))  # exception raised if cannot access or parsing error
    for sname in scp.sections():
        converted[sname] = {}
        for (key, val_text) in scp.items(sname):
            try:
                converted[sname][key] = coerce_to_type(val_text)
            except Exception as ex:
                # nre-wrap to include context of parse error and not just val_text
                raise ParseError("[%s] %s = %s (error: %s)" % (sname, key, val_text, str(ex)))
    return converted

def send_mail(sender, recipient, body, subject=None, refer=None, auth=None):
    headers = "To: %s\nFrom: %s\n" % (recipient, sender)
    if subject: headers += "Subject: %s\n" % subject  # if subject not given as arg, should be first line of body
    if refer: headers += "In-Reply-To: %s\nReferences: %s\n" % (refer, refer)
    content = "%s\n%s" % (headers, body)

    try:
        smtp = smtplib.SMTP("myth-smtp.stanford.edu", timeout=3)  # default timeout can be long, avoid mysterious stall
        try:
            smtp.starttls()  # TLS required by smtp.stanford.edu when running on cli?
        except smtplib.SMTPException:
            pass             # if starttls from web server, rejects as not supported, seems ok to ignore and continue
        if auth: smtp.login(*auth)
        smtp.sendmail(sender, [recipient], content)
        smtp.quit()
    except smtplib.SMTPException:
        import gen
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_")
        fd, name = tempfile.mkstemp(prefix=ts, dir="%s/emails" % gen.COURSE_PATH)
        with os.fdopen(fd, "w") as f:
            f.write("%s\n" % content)

def all_subclasses(cls):
    return cls.__subclasses__() + [grandkid for kid in cls.__subclasses__() for grandkid in all_subclasses(kid)]


class OptionParser(object):
    """Intended to take some of the pain out of getopt for command-line arguments"""

    def __init__(self, s=[], l=[]):
        """each short options is a 3-tuple (shortflag, name, defaultvalue)
            each long option is 2-tuple (longflag, longvalue)
            shortflag is "-x" or "-x:", val stored as args().name (init to defaultvalue)
            longflag is "--key" or "--key=", all long options store longvalue to args().long and
            store command-line arg as args().long_arg. Both long, long_arg init to None"""
        self.short = dict([(opt[0].strip(":"), opt[1]) for opt in s])
        self.long = dict([(opt[0].strip("="), opt[1]) for opt in l])
        self.shortkeys = "".join((opt[0].strip("-") for opt in s))
        self.longkeys = [opt[0].strip("-") for opt in l]
        self.options = dict([(opt[1], opt[2]) for opt in s] + [("long", None), ("long_arg", None)])

    def process_options(self, argv):
        """returns 2-tuple. [0] Struct of processed options from argv (according to short/long keys)
        [1] list of parameters (non-option arguments) remaining in argv """
        try:
            # getopt will raise if any -arg is not in shortkeys/longkey
            (matched, remaining) = getopt.gnu_getopt(argv, self.shortkeys, self.longkeys)
        except getopt.GetoptError as e:
            raise UsageError(str(e))
        for flag, val in matched:
            self.process_one(flag, val)
        return (Struct(**self.options), remaining)

    def process_one(self, flag, val):
        if flag in self.short:
            name = self.short[flag]
            if isinstance(self.options[name], bool):
                self.options[name] = True
            elif isinstance(self.options[name], list):
                self.options[name].append(val)
            else:
                self.options[name] = val
        elif flag in self.long:
            if self.options["long"]: raise UsageError("Conflicting long options '%s'" % flag)
            self.options["long"] = self.long[flag]
            self.options["long_arg"] = val

class LockedFile(object):
    """ File object that protects from concurrent modification. """
    DELAY = 0.1  # Seconds between lock attempts
    SUFFIX = ".lock"

    def __init__(self, fname, mode="r"):
        self.fname = fname
        self.mode = mode
        self.file = None
        self.lockfd = -1

    def lock(self):
        while self.lockfd == -1:
            try:
                self.lockfd = os.open(self.fname + self.SUFFIX, os.O_CREAT | os.O_EXCL)
            except OSError as ex:
                if ex.errno != errno.EEXIST: raise
                time.sleep(self.DELAY)

    def unlock(self):
        os.close(self.lockfd)
        os.unlink(self.fname + self.SUFFIX)
        self.lockfd = -1

    def __enter__(self):
        self.lock()
        self.file = open(self.fname, self.mode)
        return self.file

    def __exit__(self, type, value, traceback):
        self.file.close()
        self.file = None
        self.unlock()

    def __del__(self):
        if self.file is not None: self.file.close()
        if self.lockfd != -1: self.unlock()
