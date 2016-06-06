import subprocess
import time
import os

import pyalpm


from plaur import gitwrapper
from plaur import srcinfo

from plaur.utils import *


class Package:
    # Package represents a concrete section of a PackageConfig
    def __init__(self, pacconf, path):
        # link to parent PackageConfig
        self.pacconf = pacconf
        self.path = path # path relative to plaur-repo
        if not self.path in self.pacconf.config:
            raise UserErrorMessage("Invalid package path »%s«" % path)
        self.settings = self.pacconf.config[self.path]
        self.fullpath = self.pacconf.git.work_tree() + "/" + self.path # absolute filepath
        self.git = gitwrapper.Git(self.fullpath)
        self.srcinfo = srcinfo.SRCINFO(self.fullpath + '/.SRCINFO')
        self.vcs_pkgver_cache = None

    def fetch(self):
        if not os.path.isdir(self.fullpath):
            url = self.settings['url']
            # FIXME: package_git.call_success("clone", url) somehow ignores the --git-dir
            if 0 != subprocess.call(["git", "clone", url, self.fullpath]):
                raise UserErrorMessage("git clone failed for %s" % self.path)
        else:
            self.git.call_success("pull", "--ff-only")

    def fetch_sources(self):
        """Fetch sources needed to build the package"""
        self.assert_verified()
        makepkg = ['makepkg', '--nobuild']
        logfile = 'fetch-sources-%s.log' % time.strftime('%Y-%m-%d-%H-%M')
        logfile = os.path.join(self.fullpath, logfile)
        with open(logfile, "w") as outfile:
            proc = subprocess.Popen(makepkg, cwd=self.fullpath, stdout=outfile, stderr=outfile)
            proc.wait()

    def last_verified(self):
        last_verified = self.settings['verified']
        if last_verified == '':
            last_verified = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'
        return last_verified

    def assert_verified(self):
        """If not verified, raise a PackageUnverified exception"""
        self.git.assert_exists()
        if self.last_verified() != self.git.HEAD():
            raise PackageUnverified(self.path)

    def is_verified(self):
        return self.last_verified() == self.git.HEAD()

    def dependencies(self):
        """Return a traversable of package names this package depends on"""
        self.srcinfo.load()
        deps = self.srcinfo.query_any('makedepends')
        deps += self.srcinfo.query_any('depends')
        deps += self.srcinfo.query_any('checkdepends')
        return srcinfo.SRCINFO.drop_version_constraints(deps)

    def provides(self):
        """Return a traversable of package names this package provides on"""
        self.srcinfo.load()
        provs = list(self.srcinfo.packages())
        provs += self.srcinfo.query_any('provides')
        return srcinfo.SRCINFO.drop_version_constraints(provs)

    def vcs_pkgver(self):
        """If verified, return the VCS version using pkgver() in PKGBUILD"""
        self.assert_verified()
        if self.vcs_pkgver_cache != None:
            return self.vcs_pkgver_cache 
        command = """
        pkgver() { true; } ;
        srcdir='src/' ;
        . PKGBUILD ;
        pkgver
        """
        bash = ["bash", "-c", command]
        proc = subprocess.Popen(bash, cwd = self.fullpath, stdout=subprocess.PIPE)
        proc.wait()
        self.vcs_pkgver_cache = proc.stdout.read().decode("utf-8").strip('\n')
        return self.vcs_pkgver_cache

    def packagelist(self):
        """If .SRCINFO exists, return a list of packages"""
        self.srcinfo.load()
        package_names = self.srcinfo.package_names()
        if self.is_verified():
            new_version = self.vcs_pkgver()
            if new_version != "":
                for p in package_names:
                    p.ver = new_version
        return package_names

    def is_built(self):
        """Tell whether all packages created by that package exist """
        for f in self.packagelist():
            f = os.path.join(self.fullpath, str(f))
            if not os.path.isfile(f):
                return False
        return True

    def uninstalled_packages(self):
        """Tell which packages by this package are not installed"""
        alpm = ALPM.get()
        local_db = alpm.get_localdb()
        uninstalled = [ ]
        for f in self.packagelist():
            dep = f.name + '=' + f.ver + '-' + f.rel
            if pyalpm.find_satisfier(local_db.pkgcache, dep):
                continue
            else:
                uninstalled.append(f)
        return uninstalled

    def build(self):
        self.assert_verified()
        print("  Running makepkg in %s" % self.path)
        makepkg = ['makepkg']
        makepkg += [ ]
        logfile = 'build-%s.log' % time.strftime('%Y-%m-%d-%H-%M')
        logfile = os.path.join(self.fullpath, logfile)
        with open(logfile, "w") as outfile:
            proc = subprocess.Popen(makepkg, cwd=self.fullpath, stdout=outfile, stderr=outfile)
        print("  For live logging, type:\n  tail -f %s" % logfile)
        status = proc.wait()
        if status != 0:
            print("  makepkg failed with exit status %d:" % status)
            with open(logfile) as f:
                lines = f.read().strip('\n').split('\n')
                for l in lines[-10:]:
                    print("    " + l)

    @staticmethod
    def install(packagelist):
        asexplicit = [ ]
        asdeps = [ ]
        files = [ ]
        for package in packagelist:
            for f in package.packagelist():
                files.append(os.path.join(package.fullpath, str(f)))
                if package.settings.getboolean('asdeps', fallback=False):
                    asdeps.append(f.name)
                else:
                    asexplicit.append(f.name)
        if not files:
            # nothing to install
            return
        pacman = [ 'sudo', 'pacman', '-U', '--noconfirm' ]
        pacman += files
        proc = subprocess.Popen(pacman)
        status = proc.wait()
        if asexplicit:
            pacman = [ 'sudo', 'pacman', '-D', '--asexplicit' ]
            pacman += asexplicit
            proc = subprocess.Popen(pacman)
            status = proc.wait()
        if asdeps:
            pacman = [ 'sudo', 'pacman', '-D', '--asdeps' ]
            pacman += asdeps
            proc = subprocess.Popen(pacman)
            status = proc.wait()


