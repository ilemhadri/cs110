#!/usr/bin/python

import re

def filter_sunet(str):
    str = re.sub('.* hashes to', '<path> hashes to', str)
    return str

def strip_X11_forwarding_messages(str):
    str = filter_sunet(str)
    str = re.sub('/usr/class/xauth:.*\n', '', str)
    str = re.sub('/usr/class/xauth:.*$', '', str)
    str = re.sub('Warning: No xauth data.*\n', '', str)
    str = re.sub('Warning: No xauth data.*$', '', str)
    str = re.sub('ssh_exchange_identification.*\n', '', str)
    str = re.sub('ssh_exchange_identification.*', '', str)
    str = re.sub('DISPLAY.*\n', '', str)
    str = re.sub('DISPLAY.*$', '', str)
    str = re.sub('bash:.*Connection timed out\n', '', str)
    str = re.sub('bash:.*Connection timed out$', '', str)    
    return str

class MRCustom(CustomOutputDiffSoln):
    def init_from_string(self, line, num):
        self.name = "Custom-%d" % num
        command_str = line.strip()  # remove leading/trailing whitespace
        assert(command_str.startswith("$mr")), "Not a valid command (must start with $mr)" % command_str

        self.command = "make directories filefree >/dev/null && $core_cmd %s" % command_str
        self.soln_path = self.filepath
        return self

