
"""A git wrapper"""

from plaur.utils import *
import plaur

import subprocess
import os
import sys
import re
import subprocess

class Git:
    # create a wrapper objects to access the git repository
    # whose git root is at path
    def __init__(self, path):
        self.git_dir = path + "/.git"
        self.git_work_tree = path

    # call a git command without redirecting stderr or stdout
    def plain_call(self, *args):
        git_prefix = [ 'git',
                       '--work-tree=' + self.git_work_tree,
                       '--git-dir=' + self.git_dir,
        ]
        command = git_prefix + list(args)
        debug("Calling »%s«" % ' '.join(command))
        proc = subprocess.Popen(command)
        return proc.wait()

    # call a git subcommand, returning a tuple:
    # stdout,stderr,status
    def call(self, *args):
        git_prefix = [ 'git',
                       '--work-tree=' + self.git_work_tree,
                       '--git-dir=' + self.git_dir,
        ]
        command = git_prefix + list(args)
        debug("Calling »%s«" % ' '.join(command))
        proc = subprocess.Popen(command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        status = proc.wait()
        stdout = proc.stdout.read().decode("utf-8")
        stderr = proc.stderr.read().decode("utf-8")
        return stdout, stderr, status

    # call a successful, i.e. raise an UserErrorMessage
    # if the command exists with a status other than 0.
    # returns stdout as a string
    def call_success(self, *args):
        out,err,status = self.call(*args)
        if status != 0:
            err = re.sub("[\r\n]*$", "", err)
            cmd = ' '.join(list(args))
            if err == '':
                raise UserErrorMessage("git %s failed with status %d." % (cmd, status))
            else:
                raise UserErrorMessage("git %s failed with status %s: %s" %
                                        (cmd, status, err))
        if err != '':
            # just pass stderr
            print("git: %s" % err, file=sys.stderr)
        return out

    # tells wether a certain file is tracked by git
    # filepath can either be absolute or relative to the CWD
    def is_tracked(self, filepath):
        _,_,status = self.call('ls-files', '--error-unmatch', filepath);
        return (status == 0);

    # tells whether the git is a plaur repository
    def is_plaur_repo(self):
        pf = os.path.join(self.git_work_tree, plaur.config.plaur_ini)
        return self.is_tracked(pf);

    # returns the CWD relative to the root of the working tree
    def prefix_of_cwd(self):
        return self.call_success('rev-parse', '--show-prefix').strip()

    # returns the absolute path of the working dir
    def work_tree(self):
        return self.git_work_tree

    # tells whether the git exists in the file system
    def exists(self):
        return os.path.isdir(self.git_work_tree) and os.path.isdir(self.git_dir)

    # exit with an error message if the git directory does not exist
    def assert_exists(self):
        if not os.path.isdir(self.git_dir):
            raise UserErrorMessage("Git directory %s does not exist" % self.git_dir)
        if not os.path.isdir(self.git_work_tree):
            raise UserErrorMessage("Git work tree %s does not exist" % self.git_work_tree)

    def HEAD(self):
        return self.call_success('rev-parse', 'HEAD').strip()

# return the absolute path of the git root for the current working directory
# without trailing slashes, or None, if cwd does not live in a git repository
def detect_git(cwd='.'):
    cmd = ['git', 'rev-parse', '--show-toplevel']
    proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            cwd=cwd)
    status = proc.wait()
    stdout = proc.stdout.read().decode("utf-8")
    stderr = proc.stderr.read().decode("utf-8")
    if status == 0 and stderr == '':
        return re.sub('[/\r\n]*$', '', stdout)
    else:
        return None;
