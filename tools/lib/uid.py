
"""
Julie Zelenski, 2016-present

New module added to gather little utilities that are uid-specific.
"""

import pwd
import util
from pairing import Pairing


""" Some notes on use of ldapsearch:
    -x use simple authentication (required)
    -h ldap.stanford.edu (not needed, default ok)
    -b dc=stanford,dc=edu (sets search base, not needed, default ok)
    -LLL removes comments/version from output
    can name fields of interest at end of command, but it seems to always want to return dn also
 """

def is_valid_username(username):
    try:
        pwd.getpwnam(username)
        return True
    except KeyError:
        return False

def dept_of(username):
    try:
        found = util.system("ldapsearch -LLL -x uid=%s description" % username, exit=False)
        return util.match_regex("description: (.*)", found)
    except:
        return ""

def realname_of(username):
    try:
        return pwd.getpwnam(username).pw_gecos
    except KeyError:
        found = util.system("ldapsearch -LLL -x uid=%s gecos" % username)
        return util.match_regex("gecos: (.*)", found)

def pairings_match(username, to_include, to_exclude):
    """takes a list of terms and returns True if sunet's pairings (ta or tags) match any term.
        if empty includes all, empty excludes none"""
    mytags = student_pairings().tags_for_sunet(username)
    return (not to_include or any(t in to_include for t in mytags)) and not any(t in to_exclude for t in mytags)

def is_tagged(username, tag):
    return tag in student_pairings().tags_for_sunet(username)

def student_pairings():
    return Pairing.for_assign("students")

def tag_username(username, tag):
    student_pairings().tag_sunet(username, tag)
