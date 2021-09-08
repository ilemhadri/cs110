
"""
Julie Zelenski, 2016

This module defines top-level handlers (one for CLI, one for CGI)
Handlers intended to be installed as sys.excepthook to handle uncaught exceptions
Actions available to inform staff, display diagnostics, enter debugger
"""

import cgitb, getpass, os, signal, socket, sys, tempfile, traceback
import gen, ui, util

# bit-masks for different handler actions
INFORM_STAFF, DISPLAY_FULL, DISPLAY_TRACEBACK, DISPLAY_MESSAGE, ENTER_DEBUGGER = (2**n for n in range(5))

# this global is a cheap hack. When an exception raised during mako render, a local
# try/catch grabs the annotated mako traceback at the time and stores in saved_mako global
# (exception, traceback) and then re-raises the exception
# if end up in this handler, it uses this global to recover that saved traceback
saved_mako = (None, None)


class ExceptHook(object):
    """Object intended to install as sys.excepthook, makes nicely formatted tracebacks to be emailed/logged/displayed"""

    installed = None

    @classmethod
    def report_error(cls):
        if cls.installed:
            cls.installed.inform_staff(sys.exc_info())

    def __init__(self, actions, **kwds):
        self.actions = actions  # bit flags about what to do on uncaught exception
        self.nlines_in_traceback = 1
        # self.context contains any extra info to be dumped with report
        self.context = util.Struct(host=socket.gethostname(), cwd=os.getcwd(), command=" ".join(sys.argv), **kwds)
        self.standard_message = "The %s tool cannot complete." % self.context.tool

    def __call__(self, etype, evalue, etb):  # invoked on uncaught exception
        if etype is KeyboardInterrupt:  # (e.g. ctrl-c) treat as user-cancel, no error diagnostic
            ui.exit_cancel()
        exc_info = (etype, evalue, etb)
        self.log_action(exc_info)           # short
        if self.actions & INFORM_STAFF:
            self.inform_staff(exc_info)     # email full diagnostic for staff
        self.display_report(exc_info)       # write content to console/browser
        if self.actions & ENTER_DEBUGGER:
            self.enter_debugger(exc_info)   # start debugger at point of error

    def inform_staff(self, exc_info):
        """Tries to send full text report via email, if that fails, will drop a log file instead"""
        diagnostic = ExceptHook.full_report(self, exc_info)  # force base class to get text version
        try:
            sender = "Coursetools failure <noreply@stanford.edu>"
            subject = "ERROR %s %s" % (self.context.tool, self.context.user)
            util.send_mail(sender, gen.STAFF_EMAIL, diagnostic, subject)
        except Exception:   # if email failed
            try:
                filename = "uncaught_%s_%s_%s_" % (self.context.tool, self.context.user, ui.timestamp("%m_%d_%H%M"))
                (fd, path) = tempfile.mkstemp(prefix=filename, dir=os.path.join(gen.PRIVATE_DATA_PATH, "logs"))
                with os.fdopen(fd, "w") as file:
                    file.write(diagnostic)
                    file.write("\nSECONDARY EXCEPTION (raised within handler)\n")
                    file.write(''.join(self.text_traceback(sys.exc_info())))
            except Exception:   # both email and log failed, give on informing staff
                return
        self.standard_message += " An error diagnostic has been sent to the staff."

    def log_action(self, exc_info):
        try:
            path = os.path.join(gen.PRIVATE_DATA_PATH, "logs", "uncaught.log")
            action = "%s %s %s %s\n" % (ui.timestamp(), self.one_line_summary(exc_info), self.context.tool, self.context.user)
            if not gen.JZ_RUNNING:
                util.append_to_file(action, path)
        except Exception:
            pass  # if cannot write, don't freak out

    def one_line_summary(self, exc_info):
        return traceback.format_exception_only(exc_info[0], exc_info[1])[0].strip()

    def display_report(self, exc_info):
        if self.actions & DISPLAY_FULL:
            content = self.full_report(exc_info)
        elif self.actions & DISPLAY_TRACEBACK:
            content = self.text_traceback(exc_info)
        elif self.actions & DISPLAY_MESSAGE:
            content = self.one_line_summary(exc_info) + "\n\n" + self.standard_message
        else:
            content = self.one_line_summary(exc_info)
        self.display(content)

    def full_report(self, exc_info):
        """Full report includes traceback with dump of values for parameters/variables"""
        try:
            raw = cgitb.text(exc_info, context=self.nlines_in_traceback)
            # in the HTML report, cgitb skips printing Exception vars named ___*
            # sadly, the text version doesn't also do that, so I hackily remove them here
            # (there are gobs and they don't add value, just clutter report)
            cleaned = '\n'.join(line for line in raw.split('\n') if not line.startswith("    __"))
        except:
            cleaned = "(cgitb failed us)"
        return "%s\n%s\n\n%s\n\n%s" % (str(self.context), self.one_line_summary(exc_info), self.text_traceback(exc_info), cleaned)

    def text_traceback(self, exc_info):
        if saved_mako[0] == exc_info[0]:  # substitute saved mako traceback
            return saved_mako[1]
        else:
            return ''.join(traceback.format_exception(*exc_info))

    def display(self, content):
        """Text version just outputs to stdout in red, CGI override (below) will wrap html"""
        print "\n" + ui.red(content)

    def enter_debugger(self, exc_info):
        print ui.blue('\nEntering debugger...')
        import pdb
        pdb.post_mortem(exc_info[2])


class CGIExceptHook(ExceptHook):

    def __init__(self, actions, **kwds):
        super(CGIExceptHook, self).__init__(actions, **kwds)
        self.has_reset = False
        self.standard_message = "FATAL UNCAUGHT ERROR: The page was unable to load."

    def reset(self):
        reset_all = '''Content-Type: text/html

<!--: spam
Content-Type: text/html

<body bgcolor="#f0f0f8"><font color="#f0f0f8" size="-5"> -->
<body bgcolor="#f0f0f8"><font color="#f0f0f8" size="-5"> --> -->
</font> </font> </font> </script> </object> </blockquote> </pre>
</table> </table> </table> </table> </table> </font> </font> </font>'''
        print reset_all
        self.has_reset = True

    def display(self, content):
        """override to reset browser before sending any content, also wrap plaintext in <pre>"""
        if not self.has_reset:
            self.reset()
        if content.strip().startswith("<"):  # rough guess of whether content is html or text
            print content
        else:
            print "<pre>%s</pre>" % content

    def full_report(self, exc_info):
        """override to supply HTML-ified version and tack on the extra data"""
        extra_info = "<pre>%s\n%s</pre>" % (str(self.context), self.text_traceback(exc_info))
        try:
            html = cgitb.html(exc_info, context=self.nlines_in_traceback)
        except:
            html = "(cgitb failed us)"
        return extra_info + html


# Use install_for_cli for command-line tool, cgi for web
# can include keyword arguments of any add'l data desired to include in error report
# (leave empty and will use default info)

def install_for_cli(**kwds):

    # python resets signal handling for SIGPIPE to ignore and thus will present
    # as IOError when trying to read/write closed pipe
    # sanitycheck|head totally blows up, and when it does handler can't
    # print either, much sadness ensues.
    # make SIGPIPE terminate by resetting to default here
    # see http://bugs.python.org/issue1652
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    if "user" not in kwds: kwds["user"] = getpass.getuser()
    if "tool" not in kwds: kwds["tool"] = os.path.basename(sys.argv[0])
    if gen.is_instructor(kwds["user"]):
        what_to_do = ENTER_DEBUGGER
    elif kwds["user"] in gen.STAFF:
        what_to_do = DISPLAY_TRACEBACK
    else:
        what_to_do = INFORM_STAFF | DISPLAY_MESSAGE
    sys.excepthook = ExceptHook(what_to_do, **kwds)
    ExceptHook.installed = sys.excepthook

def install_for_cgi(**kwds):
    if "user" not in kwds: kwds["user"] = getpass.getuser()  # uses cgi-user if not otherwise given
    if "staffuser" not in kwds: kwds["staffuser"] = None
    if "tool" not in kwds: kwds["tool"] = "cgi"
    if kwds["user"] in gen.INSTRUCTORS or kwds["staffuser"] in gen.INSTRUCTORS:
        what_to_do = DISPLAY_FULL   # for, instructors dump in browser (sometimes dump to browser isn't good enough, but MC isn't watching the email list)
    elif kwds["user"] in gen.STAFF or kwds["staffuser"] in gen.STAFF:
        what_to_do = INFORM_STAFF | DISPLAY_FULL    # for TA, dump in browser, but also email/log
    else:
        what_to_do = INFORM_STAFF | DISPLAY_MESSAGE  # student gets simple message in browser, email/log
    sys.excepthook = CGIExceptHook(what_to_do, **kwds)
    ExceptHook.installed = sys.excepthook
