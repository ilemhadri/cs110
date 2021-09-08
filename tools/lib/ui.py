
"""
Julie Zelenski, 2011-present

The ui module has various niceties for formatting text (strings, dates, numbers), wrapping with color
It also defines routines for interacting with user (prompt, reading/validating input)
(this module was originally known as the formatting module and some of the functions were
originally defined in gen)
"""

import curses.ascii, datetime, locale, math, operator, os, re, sys, warnings
import mako.lookup
import gen, hooks, util

def print_stderr(msg):
    sys.stdout.flush()
    sys.stderr.write('\n' + red(msg) + '\n')
    sys.stderr.flush()

# The story about the various exit_* methods: all exit, but report
# situation slightly differently (with more/less alarm to user)
#
# exit_error: cannot continue due to user-correctable fatal error (e.g. command typo, file not found)
# exit_cancel: user action took action to quit (e.g. control-C, answered no to confirm)
# exit_done: task cannot complete, user-correctable  (e.g. in wrong dir)

def exit_cancel():
    print faint("\n[%s canceled by user]" % os.path.basename(sys.argv[0]))
    sys.exit(1)

def exit_error(msg=None):
    if msg is None: msg = "%s cannot continue." % os.path.basename(sys.argv[0])
    print_stderr("[FATAL ERROR] %s" % msg)
    sys.exit(1)

def exit_done(msg):
    print_stderr(msg)
    sys.exit(1)

def confirm_or_exit(prompt, default=None):
    if not get_yes_or_no(prompt, default):
        exit_cancel()

def warn(msg):
    warnings.warn(bold(msg))

def with_commas(num):
    locale.setlocale(locale.LC_ALL, "en_US.utf8")
    return locale.format("%d", num, grouping=True)

def without_commas(str):
    return str.replace(',', '')

def pretty_list(list, maxitems=-1):
    """Calls str on each item to get more human-readable form, by default no abbreviate"""
    if maxitems != -1 and len(list) > maxitems:
        list = list[0:maxitems] + ["..."]
    # recognizes list that represents range and reports as such
    if len(list) >= 2 and isinstance(list[0], int) and isinstance(list[-1], int) and list == range(list[0], list[-1]+1):
        return "[%s to %s]" % (list[0], list[-1])
    return "[%s]" % (", ".join((str(item) for item in list)))

def abbreviate_list(list, maxitems=10):
    return pretty_list(list, maxitems)

def abbreviate(str, maxlines=8, maxlen=500):
    """Used to abbreviate long output in student grade reports.  Default is to
    grab first 8 (or maxlines) lines and truncate to first 500 (or maxlen) chars"""
    lines = str.split('\n')
    if len(str) <= maxlen and len(lines) <= maxlines:  # no abbreviation needed
        return str
    if len(str) > maxlen:  # truncate total output
        str = str[:maxlen]
        lines = str.split('\n')
    if len(lines) > maxlines:  # truncate to first maxlines
        str = ('\n'.join(lines[:maxlines])) + '\n'
    return str + "..."

def convert_nonascii(s):
    result = ''
    for ch in s:
        if not curses.ascii.isascii(ch):
            result += "\%d" % ord(ch)
        elif not curses.ascii.isprint(ch) and ch != '\r' and ch != '\n' and ch != '\t':
            result += curses.ascii.unctrl(ch)
        else:
            result += ch
    return result

def convert_control_chars(s):
    return ''.join([curses.ascii.unctrl(ch) if (curses.ascii.isctrl(ch) and ch not in "\r\n\t") else ch for ch in s])

def pretty_diffs(dmp, diffs):
    results = []
    for (op, data) in diffs:
        if op == dmp.DIFF_INSERT:
            results.append(red(data))
        elif op == dmp.DIFF_DELETE:
            results.append(underline(data))
        elif op == dmp.DIFF_EQUAL:
            results.append(data)
    return "".join(results)

def try_utf8(s):
    try: return s.decode("utf-8")
    except UnicodeError: return "".join([c for c in s if ord(c) < 128])

def nicetitle(str, width, ch='-'):
    return (" " + bold(str) + " ").center(width, ch)

def nicedate(x):
    return nicedatetime(x, format="%a %b %d")

def niceduedate(x):
    return nicedatetime(x, format="%a %b %-d %-I:%M %P")

def nicedatetime(x, format="%a %b %d %H:%M"):
    if isinstance(x, float):
        x = datetime.datetime.fromtimestamp(x)
    if isinstance(x, datetime.datetime):
        return x.strftime(format)
    else:
        return x

def timestamp(format="%a %b %d %H:%M"):
    return nicedatetime(datetime.datetime.now(), format)

def nicetime(t=None):
    return nicedatetime(t if t else datetime.datetime.now(), format="%H:%M")

def timetag(t=None):
    if not t: t = datetime.datetime.now()
    return t.strftime("%m%d_%H%M%S")

def fraction(numer, denom):
    ndigits = int(math.log10(denom)) if denom else 0
    return "{:{ndigits}d}/{}".format(numer, denom, ndigits=ndigits)

def percentage(numer, denom, verbose=True):
    val = int(round(100.0*numer)/denom if denom else 0)
    return "{}{:4d}%".format(fraction(numer, denom) if verbose else "", val)

def plural(num):
    return '' if num == 1 else 's'

def render_internal(template, **kwargs):
    """If error raised during render, grab Mako-enhanced traceback at time of raise
    and store to hook so can be shown later which gives slightly better reporting
    of what went wrong"""
    try:
        return template.render(**kwargs)
    except:
        mako_traceback = mako.exceptions.text_error_template().render()
        msg = "Exception raised within render of mako template %s" % mako_traceback
        hooks.saved_mako = (sys.exc_info()[0], msg)
        raise

def render_template(templatename, templatedir=os.path.join(gen.PRIVATE_DATA_PATH, "templates"), **kwargs):
    # strict undefined produces slightly more informative error on use of unknown var in template
    t = mako.lookup.TemplateLookup(directories=[templatedir], strict_undefined=True).get_template(templatename)
    return render_internal(t, **kwargs)

def render_text(text, templatedir, **kwargs):
    t = mako.lookup.Template(text, lookup=mako.lookup.TemplateLookup(directories=[templatedir], strict_undefined=True))
    return render_internal(t, **kwargs)

def get_input(prompt):
    try:
        return raw_input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        # EOF will result if user entered Ctrl-D or stdin pipe hit dead end
        # re-map to Ctrl-C (interrupt) and hook will handle as user cancel/interrupt
        print  # print CR to advance output beyond prompt to next line for any message printed
        raise KeyboardInterrupt

def get_choice(prompt, options, default=None, allow_comment=False, cmp=operator.contains):
    """The mother of all input routines.  Client lists valid options. Will prompt user
    to enter response, returns choice if valid (e.g. appears in list of options), otherwise retry.
    The options in list can be strings/numbers (or anything for which str() works). If there
    is a default, it will be used when user enters empty string.  If allow_comment is True,
    will parse first token as choice and return tuple (choice, rest of line). Default match operation
    is contains (i.e. substring match). use operator.eq for equality or str.startswith for prefix match"""
    if default:
        offer = " [%s]:" % default
    elif len(options) == 2:
        offer = " [%s]:" % '/'.join([str(o) for o in options])
    else:
        offer = " "
    while True:
        response = get_input(prompt + offer)
        if response == "":
            if default:
                choice,comment = (default, "")
                break
        else:
            tokens = response.split()
            choice,comment = (tokens[0], ' '.join(tokens[1:]))
            choice = util.unique_match(choice, options, cmp)
            if choice is not None: break
            print "Try again. Options are %s" % pretty_list(options)
    return (choice, comment) if allow_comment else choice

def get_yes_or_no(prompt, default=None):
    return get_choice(prompt, ["y", "n"], default=default, allow_comment=False) == "y"

def get_number(prompt, rg, default=None, allow_comment=False):
    """Requires range of valid numbers to compare response"""
    return get_choice(prompt, rg, default, allow_comment=allow_comment, cmp=operator.eq)

def get_lettered_choice(options, allow_comment=False):
    """Choices is list of strings, prints menu (lettered), gets user's choice as letter, returns position of letter in list"""
    print "Choose from: "
    for i, option in enumerate(options):
        print "%4s) %s" % (chr(i+ord('a')), option)
    answer = get_choice("Enter choice:", [chr(i+ord('a')) for i in range(len(options))], allow_comment=allow_comment)
    position = ord(answer[0]) - ord('a')  # answer[0] works whether answer is tuple or string, almost (but not entirely) accidental :-)
    return (position, answer[1]) if allow_comment else position

LASTLEN = 0
def overprint(str='\n'):
    """When done overprinting, best to call overprint(no-arg or <string ending in newline>) to wipe out notion of lastlen"""
    global LASTLEN
    if LASTLEN: sys.stdout.write('\b'*LASTLEN+' '*LASTLEN+'\b'*LASTLEN)  # "erase" previous
    sys.stdout.write(str)
    sys.stdout.flush()
    if str.endswith('\n'):
        LASTLEN = 0
    else:
        LASTLEN = len(str)
    return True

# remember: msgcat --color=test to see other possibilities
COLORS = {"normal":"\033[0m", "red":"\033[31m", "blue":"\033[34m", "green":"\033[32m",
          "yellow":"\033[33m", "cyan":"\033[36m", "magenta":"\033[35m", "underline":"\033[4m",
          "bold":"\033[1m", "faint":"\033[2m", "inverse":"\033[7m",
          # "italic":"\033[3m", "strikethrough":"\033[9m",
          }

def wrap(colorstr, text):
    """Wraps text in ansi color given by color string, ends with normal"""
    # MC: My terminal is dark, so I want all the colors bold...
    return (COLORS["bold"] if "BOLD_COLORS" in os.environ and colorstr != "faint" else "") + COLORS[colorstr] + text + COLORS["normal"]

def stripcolors(text):
    """Remove all ansi color sequences from text """
    ansi_color_regex = chr(27) + "\[[0-9;]*m"
    text = re.sub(ansi_color_regex, "", text)
    escape_regex = chr(27) + "\[K"  # these are being emitted by gcc, what other esc to watch for?
    text = re.sub(escape_regex, "", text)
    return text

def fn_for(color):
    return lambda s: wrap(color, str(s))  # pull lambda out of loop to get the right closure

# Loading the formatting module adds named methods to wrap strings with color directives
# e.g. ui.red(string)
# this is unnecessary but cute (am I having too much fun playing with Python??)
for color in COLORS:
    setattr(sys.modules[__name__], color, fn_for(color))
