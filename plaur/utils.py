import sys
import re

import pyalpm
import pycman

program_name = "?"

class UserErrorMessage(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return self.message
    def print(self):
        print("%s error: %s" % (program_name, self.message))

class PackageUnverified(Exception):
    def __init__(self, path):
        self.path = path
    def __str(self):
        return "Package %s not verified" % self.path

def debug(*objs):
    #print("Debug: ", *objs, file=sys.stderr)
    return True

def error_msg(*objs):
    print("Error: ", *objs, file=sys.stderr)

# from http://stackoverflow.com/questions/566746/how-to-get-console-window-width-in-python
def getTerminalSize():
    import os
    env = os.environ
    def ioctl_GWINSZ(fd):
        try:
            import fcntl, termios, struct, os
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ,
        '1234'))
        except:
            return
        return cr
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        cr = (env.get('LINES', 25), env.get('COLUMNS', 80))

        ### Use get(key[, default]) instead of a try/catch
        #try:
        #    cr = (env['LINES'], env['COLUMNS'])
        #except:
        #    cr = (25, 80)
    return int(cr[1]), int(cr[0])

class ProgressBar:
    def __init__(self, progress = 0.0):
        self.progress = progress

    def set(self,progress):
        self.progress = progress
        self.redraw()

    def redraw(self):
        string = "\033[s\033[0;0H"
        (width, _) = getTerminalSize()
        width = width - 2
        for i in range(0, width):
            tick = int(self.progress * width)
            if i == tick:
                string += '|'
            elif i < tick:
                string += '='
            else:
                string += '.'
        string += '\033[0;0H\n\033[u'
        print(string, end="", flush=True)

# thanks to http://stackoverflow.com/questions/510357/python-read-a-single-character-from-the-user
class _GetchUnix:
    def __init__(self):
        import tty, sys

    def __call__(self):
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

def ask(message,default_yes=True):
    if default_yes:
        answers = '[Y/n]'
    else:
        answers = '[y/N]'
    print("%s %s " % (message,answers),end="",flush=True)
    ch = _GetchUnix()()
    if not ch == '\n':
        print(ch,flush=True)
    if ch.lower() == 'y':
        return True
    elif ch.lower() == 'n':
        return False
    else:
        return default_yes

def colored_header(message):
    return ("\033[0;33m========\033[1;37m %s \033[0;33m========\033[0m\n" % message)

class ALPM:
    pacman_config = None
    alpm_handle = None
    @staticmethod
    def get():
        if ALPM.alpm_handle == None:
            ALPM.pacman_config = pycman.config.PacmanConfig(conf = '/etc/pacman.conf')
            ALPM.alpm_handle = ALPM.pacman_config.initialize_alpm()
        return ALPM.alpm_handle

def alpm_depcheck(packages):
    # check the availability of the package names 'packages'
    # in the packman repository and return three (not necessarily disjoint!)
    # lists of package names of the following form:
    class DepCheckResult:
        def __init__(self):
            # Each of them is a list of required packages ...
            # ... that are installable via a (non-ignored) repository:
            self.repoinstall = [ ]
            # ... that are present in an ignored repository:
            self.repoignore = [ ]
            # ... that are not found in any pacman/alpm repository
            self.missing = [ ]
            # ... that are already installed
            self.installed = [ ]
        def __str__(self):
            sep = ', '
            return """repoinstall = %s
repoignore  = %s
missing     = %s
installed   = %s""" % (sep.join(self.repoinstall), sep.join(self.repoignore), sep.join(self.missing), sep.join(self.installed))
    res = DepCheckResult()
    alpm = ALPM.get()
    local_db = alpm.get_localdb()
    dbs = alpm.get_syncdbs()
    repo_ignore_re = re.compile("thorsten")
    for dep in packages:
        is_installed = False
        if pyalpm.find_satisfier(local_db.pkgcache, dep):
            res.installed.append(dep)
            is_installed = True
        repo_found = False
        for db in dbs:
            match = repo_ignore_re.match(db.name)
            if match and match.end() == len(db.name) and db.get_pkg(dep):
                res.repoignore.append(dep)
                continue
            pkg = pyalpm.find_satisfier(db.pkgcache, dep)
            if pkg is not None:
                #print("%s is in repo %s" % (dep,db.name))
                repo_found = True
            if pkg is not None and not is_installed:
                # mark that it still needs to be installed
                res.repoinstall.append(dep)
        if not repo_found:
            #print("%s missing" % dep)
            res.missing.append(dep)
    return res

