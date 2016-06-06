"""An AUR helper using the power of git"""

import os.path

__author__ = "Thorsten Wißmann"
__copyright__ = "Copyright 2016 Thorsten Wißmann"
__license__ = "GPL"
__maintainer__ = __author__
__email__ = "edu@thorsten-wissmann.de"
__version_info__ = (0, 1, 0)
__version__ = '.'.join(str(e) for e in __version_info__)
__description__ = "An AUR helper using the power of git"

basedir = os.path.dirname(os.path.realpath(__file__))
