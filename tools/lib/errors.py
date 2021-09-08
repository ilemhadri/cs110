"""
Trivial Exception subclassses to distinguish different varieties of error
"""


class UsageError(Exception):            # errors during argument parsing
    pass

class ConfigurationError(Exception):    # errors in config files
    pass

class ManifestError(Exception):         # errors in testing/webreview manifest
    pass

class ParseError(Exception):            # ConfigParser errors
    pass