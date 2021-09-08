"""
The imports that are universally needed
"""

import errors


# JDZ: possible for these to use msg() if callable(msg) else msg 
# and then call as asserts.config(expr, lambda: message expression)
# this allows lazy eval of message expression, only when needed

def config(expr, msg):
    if not expr:
        raise errors.ConfigurationError(msg)

def usage(expr, msg):
    if not expr:
        raise errors.UsageError(msg)

def manifest(expr, msg):
    if not expr:
        raise errors.ManifestError(msg)

def parser(expr, msg):
    if not expr:
        raise errors.ParseError(msg)
