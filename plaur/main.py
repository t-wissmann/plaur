# vim: et ts=4 sw=4
# Python 3

import subprocess
import configparser
import os
import stat
import sys
import re
import subprocess
import queue
import time
import shutil


import pyalpm
import pycman
#from pycman import config
#from pycman import action_deptest

import plaur
from plaur.utils import *
from plaur import gitwrapper
from plaur import utils
from plaur import packageconfig
import plaur.package as P
import plaur.config


# returns a Git object for the plaur repository
def assert_plaur_git():
    gitpath = gitwrapper.detect_git();
    if gitpath == None:
        raise UserErrorMessage("Not in a plaur git repository")
    git = plaur.gitwrapper.Git(gitpath)
    if not git.is_plaur_repo():
        # if this detected git is not a plaur repository,
        # then maybe it's just a pkgbuild repo, so try the parent directory as
        # well:
        (gitpath,_) = os.path.split(gitpath.rstrip('/'))
        gitpath = gitwrapper.detect_git(cwd=gitpath)
        if gitpath == None:
            raise UserErrorMessage("Not in a plaur git repository")
        git = plaur.gitwrapper.Git(gitpath)
        if not git.is_plaur_repo():
            raise UserErrorMessage("Present directory is not in a plaur repository")
    #print(gitpath)
    global config
    config.set_filename_from_git(git)
    return git

#--------------- classes  ---------------
class Command:
    def __init__(self, callback, description, is_alias=False):
        self.callback = callback
        self.description = description
        self.is_alias = is_alias


#--------------- commands ---------------
def find_command(name):
    global commands_dict
    if name in commands_dict:
        return commands_dict[name]
    else:
        raise UserErrorMessage("No such subcommand »%s«" % name)

def cmd_usage(args):
    """Usage: help [CMD]

    Print the long description of the specified subcommand CMD.
    If no CMD is given, list all the available subcommands.
    """
    if len(args) == 0:
        print("Usage: %s SUBCOMMANDS [ARGS...]" % program_name)
        print("where SUBCOMMANDS is one of the following:")
        print("")
        for name,cmd in commands:
            print("    %-10s%s" % (name,cmd.description))
    else:
        c = find_command(args[0])
        print(program_name + " " + args[0] + ": " + c.description)
        if c.callback.__doc__ != None:
            print()
            print(c.callback.__doc__.lstrip("\n "))

def cmd_init(args):
    """Usage: init

    Initialize an empty plaur repository in the current working directory"""
    git_path = gitwrapper.detect_git();
    if git_path != None:
        raise UserErrorMessage("Already a git repository in »%s«" % git_path)
    git = gitwrapper.Git(os.getcwd())
    out = git.call_success('init');
    global config
    config.set_filename_from_git(git)
    config.read()
    config.write()
    git.call_success("add", config.filename)
    # create empty packages file
    p = packageconfig.PackageConfig(git)
    p.read()
    p.write()
    git.call_success("add", p.absolute_filepath())
    git.call_success("commit", "-m", "Initial commit");

def cmd_fetch(args):
    """Usage: fetch [PATH…]

    Updates the given PATHs to the current upstream version, and creates them
    if necessary.

    If no PATH is given, then all configured paths will be fetched.
    """
    paths = args
    git = assert_plaur_git()
    packs = packageconfig.PackageConfig(git);
    packs.read();
    prefix = git.prefix_of_cwd()
    if paths:
        # prepend a prefix to paths, depending on the cwd
        paths = [ prefix + p for p in paths ]
    else:
        # if no path is given, implicitly use all paths saved
        paths = packs.paths()
    draw_progressbar = True
    #pg = ProgressBar()
    #pg.set(0.0)
    for i,p in enumerate(paths):
        #pg.set(float(i) / len(paths))
        print("Fetching %s" % p)
        packs.fetch(p)
    #pg.set(1.0)

def cmd_add(args):
    """Usage: add [--asdeps] PACKAGENAME [PATH]

    Add a package with name PACKAGENAME and put it in the directory specified
    by PATH (either absolute or relative to the current working directory).
    PATH defaults to PACKAGENAME.

    If --asdeps is supplied, then the package will be marked as being a
    dependency for another package.
    """
    asdeps = False
    if (len(args) >= 1 and args[0] == '--asdeps'):
        asdeps = True
        args = args[1:]
    if (len(args) < 1):
        raise UserErrorMessage("To few arguments")
    name = args[0]
    path = args[1] if len(args) > 1 else name
    git = assert_plaur_git()
    packs = packageconfig.PackageConfig(git)
    prefix = git.prefix_of_cwd()
    packs.read()
    packs.add(prefix+path, "https://aur.archlinux.org/%s.git" % name, asdeps = asdeps)
    packs.write()
    packs.commit("Add " + prefix + path);

def cmd_diff(args):
    """Usage: diff [PATH…]

    For the given PATHs, print the differences between the last verified
    and the current version.

    If no PATH is specified, then the difference of all paths with changes will
    be shown.
    """
    git = assert_plaur_git()
    packs = packageconfig.PackageConfig(git)
    packs.read()
    prefix = git.prefix_of_cwd()
    # TODO: use $PAGER
    pager = subprocess.Popen(['less', '-i', '-R', '-K', '-X', '--quit-if-one-screen'],
                            stdin=subprocess.PIPE,
                            )
    paths = args
    hide_if_unchanged = False
    if paths:
        # prepend a prefix to paths, depending on the cwd
        paths = [ prefix + p for p in paths ]
    else:
        # if no path is given, implicitly use all paths saved
        paths = packs.paths()
        hide_if_unchanged = True
    for fullpath in paths:
        package = packs[fullpath]
        last_verified = package.last_verified()
        diff_string = package.git.call_success('diff', '--color=always', last_verified, 'HEAD')
        if hide_if_unchanged and diff_string.lstrip() == '':
            continue
        output  = colored_header(package.path)
        output += diff_string
        output += "\n"
        pager.stdin.write(output.encode("utf-8"))
        pager.stdin.flush()
    pager.stdin.close()
    pager.wait()

def cmd_verify(args):
    """Usage: verify [PATH…]

    For the given PATHs, mark the current version as verified.
    This means, that the PKGBUILD (and the attached files) in them can be
    sourced and executed.

    If no PATH is specified, then all paths are verified interactively.
    """
    git = assert_plaur_git()
    packs = packageconfig.PackageConfig(git)
    packs.read()
    prefix = git.prefix_of_cwd()
    user_confirm = False
    show_diffs = False # this makes only sense if user_confirm is set to True
    paths = args
    if paths:
        # prepend a prefix to paths, depending on the cwd
        paths = [ prefix + p for p in paths ]
    else:
        # if no path is given, implicitly use all paths saved
        paths = packs.paths()
        user_confirm = True
        show_diffs = True
    for fullpath in paths:
        package = packs[fullpath]
        package.git.assert_exists()
        package_HEAD = package.git.HEAD();
        last_verified = package.last_verified()
        if last_verified == package_HEAD:
            print("%s up to date (on %s)." % (package.path, last_verified))
            continue
        if show_diffs:
            print(colored_header("Changes in " + package.path))
            print(package.git.call_success('diff', '--color=always', last_verified, 'HEAD'))
        if not user_confirm or ask("Verify %s to %s?" % (package.path, package_HEAD),default_yes=False):
            print ("Verifying %s to %s." % (package.path, package_HEAD))
            package.settings['verified'] = package_HEAD
            packs.write()
            packs.commit("Verify " + package.path)

def cmd_build(args):
    """Usage: build [PATH…]

    Execute makepkg in those of the given PATHs, that are verified, and skip
    the other (unverified) PATHs. After a successful build, the new packages
    are installed via pacman.
    """
    install = False
    if (len(args) >= 1 and args[0] == '--install'):
        install = True
        args = args[1:]
    git = assert_plaur_git()
    packs = packageconfig.PackageConfig(git)
    packs.read()
    paths = args
    if paths:
        # prepend a prefix to paths, depending on the cwd
        prefix = git.prefix_of_cwd()
        paths = [ prefix + p for p in paths ]
    else:
        paths = packs.paths()
        install = True
    # reorder paths according to dependencies
    (provides,dependencies) = packs.compute_depgraph(paths, provide_guessing = True)
    paths = packageconfig.PackageConfig.depsort(provides,dependencies)
    print("Building the packages: " + ' '.join(paths))
    for fullpath in paths:
        package = packs[fullpath]
        try:
            print(":: " + package.path)
            print("  fetching sources...")
            package.fetch_sources()
            if not package.is_built():
                package.build()
            else:
                print("  Built packages up to date")
            if package.uninstalled_packages():
                P.Package.install([package])
            else:
                print("  Installed packages up to date")
        except P.PackageUnverified as e:
            print(":: Skipping unverified %s" % e.path)

def cmd_git(args):
    """Usage: git [ARGS…]

    Execute some git command in the main plaur repository.

    This allows performing git commands on the plaur repo without leaving the
    current working directory. This is convenient, because often one is in a
    subdirectory which is a git repository of a PKGBUILD.
    """
    git = assert_plaur_git()
    sys.exit(git.plain_call(*args))

def cmd_asciidoc(args):
    global commands_dict
    program_name = "plaur"
    flag = re.compile('(?P<flag>--[\w-]+)')
    argname = re.compile('(?P<argname>[A-Z][A-Z0-9…]+[a-z]*)')
    print("""%s(1)
=======
:doctype: manpage


NAME
----
%s - a pleasant AUR helper using the power of git


SYNOPSIS
--------
*plaur* 'SUBCOMMAND' ['ARGS…']


DESCRIPTION
-----------
Calls the given *plaur* subcommand. The meanings of the arguments 'ARGS' depend
on the 'SUBCOMMAND'. The available commands and their meanings are described in
the <<COMMANDS,*COMMANDS*>> section.

include::plaur_concept.txt[]

[[COMMANDS]]
COMMANDS
--------
""" % (program_name, program_name) )
    for name,c in sorted(commands_dict.items()):
        if c.is_alias:
            # avoid multiple entries due to command aliases
            continue
        # extract the usage line:
        if c.callback.__doc__ == None:
            description = ""
        else:
            description = c.callback.__doc__.strip('\n ')
        description = flag.sub(r'*\1*', description)
        description = argname.sub(r"'\1'", description)
        usage_rest = description.split('\n', 1)
        if len(usage_rest) == 0 or usage_rest[0] == '':
            usage = name
            longdesc = ""
        elif len(usage_rest) == 1:
            usage = usage_rest[0]
            longdesc = ""
        else:
            usage = usage_rest[0]
            longdesc = usage_rest[1]
        if usage.startswith("Usage: "):
            usage = usage[len("Usage: "):]
        print ('\n' + usage + '::')
        print ('    __' + c.description + '__')
        print (re.compile('^$', re.MULTILINE).sub(r'    +', longdesc))
    print("""
[[FILES]]
FILES
-----
Beside the actual packages *plaur* manages two files, as described in the
following. Both are using the <<INIFILEFORMAT,*INI FILE FORMAT*>>.

[[MAINCONFIGURATION]]
MAIN CONFIGURATION: plaur.ini
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The git root of the plaur repository must contain a file named +plaur.ini+
serving two purposes. Firstly it identifies a git repository as a plaur
repository. Secondly it contains the user specific configuration. Its content
is never written by *plaur* and is intended to be edited manually by the user
if needed. The available options are available in the only file section called
+options+:

""")
    for (k,(v,d)) in config.defaults.items():
        print("'%s' (Default value: +%s+)::\n  %s" % (k,v,d))

    print("""

[[PACKAGESCONFIGURATION]]
PACKAGES CONFIGURATION: packages.ini
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the git root, a file +packages.ini+ (file name and location are configurable
in +plaur.ini+) lists the packages and their options, managed by *plaur*. It is
edited automatically via *plaur* and not intended to be written by the user.

[[INIFILEFORMAT]]
INI FILE FORMAT
~~~~~~~~~~~~~~~
All configuration files are of python's ini format:

    - Lines beginning with +#+ are treated as commetns
    - The file is divided into sections. Each section starts with a line
      +[name]+ where +name+ denotes the section name. Then multiple lines
      of the pattern +key = value+ follow.

RESOURCES
---------
Github page: http://github.com/t-wissmann/plaur
""")

def cmd_status(args):
    class Cell:
        def __init__(self,text,color=None):
            self.text = text
            self.color = color
        def width(self):
            # TODO: return utf8 string length
            return 2+len(self.text)
        def render(self,width):
            string = (" %-"+str(width-2)+"s ") % self.text
            if self.color:
                string = "\033[%sm%s\033[0m" % (self.color,string)
            return string
    class Table:
        def __init__(self):
            self.rows = [ ]
        def add_row(self,r):
            self.rows.append(r);
        def __str__(self):
            # firstly, construct the width of the columns
            colwidths = [ ]
            for r in self.rows:
                for i,c in enumerate(r):
                    if len(colwidths) <= i:
                        colwidths.append(c.width())
                    else:
                        colwidths[i] = max(colwidths[i], c.width())
            # secondly, print the table
            buf = ""
            for r in self.rows:
                for i,c in enumerate(r):
                    buf += c.render(colwidths[i])
                buf += "\n"
            return buf

    git = assert_plaur_git()
    packs = packageconfig.PackageConfig(git)
    packs.read()
    paths = args
    if paths:
        # prepend a prefix to paths, depending on the cwd
        prefix = git.prefix_of_cwd()
        paths = [ prefix + p for p in paths ]
    else:
        # if no path is given, implicitly use all paths saved
        paths = packs.paths()
    table = Table()
    hashlength = 10 # tells how short the git commit hashes are cropped
    for fullpath in paths:
        package = packs[fullpath]
        last_verified = package.last_verified()
        lvcolor = '42;30'
        headcolor = None
        if package.git.exists():
            head = package.git.HEAD()
            if head == last_verified:
                headcolor = lvcolor
            else:
                headcolor = '41;1;37'
        else:
            head = ''
        r = [
            Cell(fullpath),
            Cell(last_verified[0:hashlength],color=lvcolor),
            Cell(head[0:hashlength],color=headcolor),
        ]
        table.add_row(r)
    print(table,end="")

def cmd_depadd(args):
    """Usage: depadd [PATH…]

    For each of the given PATHs, check for unresolved dependencies and add them
    to the plaur repo or install them via pacman, if possible.
    """
    git = assert_plaur_git()
    prefix = git.prefix_of_cwd()
    packs = packageconfig.PackageConfig(git)
    packs.read()
    paths = args
    if paths:
        # prepend a prefix to paths, depending on the cwd
        paths = [ prefix + p for p in paths ]
    else:
        # if no path is given, implicitly use all paths saved
        paths = packs.paths()
    (dependencies,provides) = packs.compute_depgraph(paths,provide_guessing=True)
    unresolved_deps = [ ]
    for needed,by in dependencies.items():
        if not needed in provides:
            unresolved_deps.append(needed)
    print("unresolved: %s" % ' '.join(unresolved_deps))
    res = alpm_depcheck(unresolved_deps)
    print(res)
    pacman_command = 'sudo pacman -S --asdeps'.split(' ')
    print("Packages in ignored repositories: " + ' '.join(res.repoignore))
    print("Packages installable: " + ' '.join(res.repoinstall))
    if res.repoinstall and ask ("Install above packages via '%s'?" % ' '.join(pacman_command)):
        proc = subprocess.Popen(pacman_command + res.repoinstall)
        proc.wait()
    print("Unresolved: %s" % ' '.join(res.missing))
    if res.missing and ask ("Add unresolved packages?"):
        packs.read()
        for p in res.missing:
            path = os.path.join(prefix, p)
            url = "https://aur.archlinux.org/%s.git" % p
            packs.add(path, url, asdeps = True)
            packs.write()
            msg = ("Add dependency %s\n\n"
                + "It is required by:\n"
                + "  - %s\n") % (path, '\n  - '.join(dependencies[p]))
            #print(msg)
            packs.commit(msg)


def cmd_cat_srcinfo(args):
    """
    Usage: cat_srcinfo [FILES…]

    This command exists solely for debugging purposes:

    Read the supplied FILES of the .SRCINFO format and print them again.
    The order of options may change, however the order of different options
    with the same key stays unchanged.
    """
    for f in args:
        srcinfofile = plaur.srcinfo.SRCINFO(f)
        srcinfofile.load()
        print(srcinfofile, end="")

def cmd_cat_config(args):
    """
    Usage: cat_config

    This command exists solely for debugging purposes:

    Show the contents of the plaur.ini of the present plaur repository.
    """
    assert_plaur_git()
    config.print_contents()

def cmd_why(args):
    """
    Usage: why [PACKAGES…]

    For the given PACKAGES, why they are in the plaur repository. That is, tell
    whether it was added explicitly or as a dependency, and tell by which other
    packages it is needed.
    """
    git = assert_plaur_git()
    packs = packageconfig.PackageConfig(git)
    packs.read()
    (deps,provs) = packs.compute_depgraph(packs.paths(), provide_guessing=True)
    paths = args
    if paths:
        prefix = git.prefix_of_cwd()
        paths = [ os.path.join(prefix, p) for p in paths ]
    else:
        paths = packs.paths()
    for package in [ packs[p] for p in paths ]:
        if package.settings.getboolean('asdeps', fallback=False):
            print("%s was added as a dependency." % package.path)
        else:
            print("%s was added explicitly." % package.path)
        for name,provided_by in provs.items():
            if package.path in provided_by:
                msg = "  %s required by: " % name
                l = deps.get(name, [])
                msg += ' '.join(l) if l else "nothing else"
                print(msg)

def cmd_rm(args):
    """Usage: rm [PACKAGES…]

    Remove the given PACKAGES.
    """
    asdeps = False
    name = args[0]
    path = args[1] if len(args) > 1 else name
    git = assert_plaur_git()
    packs = packageconfig.PackageConfig(git)
    prefix = git.prefix_of_cwd()
    packs.read()
    packs.rm(prefix+path)
    try:
        for root, dirs, files in os.walk(path):
            for d in dirs:
              os.chmod(os.path.join(root, d),
                stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        shutil.rmtree(path)
    except FileNotFoundError as e:
        # don't do anything if the path does not exist anymore
        pass
    packs.write()
    packs.commit("Remove " + prefix + path);

#---------------   main   ---------------
commands = [
    [ "-h",      Command(cmd_usage, "Print this help", is_alias=True)],
    [ "--help",  Command(cmd_usage, "Print this help", is_alias=True)],
    [ "help",    Command(cmd_usage, "Print general help or that of a subcommand")],
    [ "init",    Command(cmd_init, "Initalize the present directory")],
    [ "add",     Command(cmd_add, "Add a new package")],
    [ "fetch",   Command(cmd_fetch, "Update or create a PKGBUILD from upstream")],
    [ "diff",    Command(cmd_diff, "Show differences since last verification")],
    [ "verify",  Command(cmd_verify, "Verify a pkgbuild")],
    [ "build",   Command(cmd_build, "Build the specified packages")],
    [ "git",     Command(cmd_git, "Run a git command on the packages repository")],
    [ "asciidoc",Command(cmd_asciidoc, "Generate documentation in asciidoc format")],
    [ "status",  Command(cmd_status, "Show package version and build status")],
    [ "st",      Command(cmd_status, "Show package version and build status", is_alias=True)],
    [ "depadd",  Command(cmd_depadd, "Add dependencies for the given packages")],
    [ "cat_srcinfo",  Command(cmd_cat_srcinfo, "Read and print the given .SRCINFO files")],
    [ "cat_config",  Command(cmd_cat_config, "Read and print the plaur.ini")],
    [ "why",  Command(cmd_why, "Tell why a package is in the plaur repository")],
    [ "rm",  Command(cmd_rm, "Remove a package")],
]


commands_dict = { }
for k,v in commands:
    commands_dict[k] = v
program_name = re.sub('^.*/', '', sys.argv[0])
config = plaur.config.PlaurConfig()

def main(argv):
    if len(argv) <= 1:
        cmd_usage([])
    else:
        try:
            c = find_command(argv[1])
            c.callback(argv[2:])
        except UserErrorMessage as e:
            e.print()
            return 1
        except KeyboardInterrupt as e:
            return 1
    return 0

