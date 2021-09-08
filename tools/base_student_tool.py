
"""
Julie Zelenski 2016

This module contains startup sequence common to the student tools (submit/sanity)
A student tool script should import this module first (before anything else)
"""

import os, re, socket, sys

""" Code below is common startup sequence
    Note lack of test for main module-- this code is expected to run on import """

# get directory where this file lives, used as base to reach out for other resources
WHERE_AM_I = os.path.dirname(os.path.normpath(os.path.realpath(__file__)))

# set import path to include location of lib
sys.path.insert(1, os.path.normpath(os.path.join(WHERE_AM_I, "lib")))
import gen, hooks

# install top-level handler for uncaught exception
hooks.install_for_cli()

# verify running on system known to have correct software, mounted filesystems, etc.
host = socket.gethostname()
if not re.match(gen.HOSTNAME_REGEX, host):
    print "You are running on %s, which is not a valid host.\nPlease log in to a valid host (e.g. myth) and re-run." % host
    sys.exit(1)

offline = os.path.join(WHERE_AM_I, "maintenance")  # look for file named maintenance in same dir as this script
if os.path.exists(offline) and not gen.is_instructor():
    print "This tool is temporarily off-line for maintenance. Thanks for your patience until resolved."
    sys.exit(1)
