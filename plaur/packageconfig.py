# vim: et ts=4 sw=4

import configparser
import os
import queue
import plaur

from plaur.utils import *


class PackageConfig:
    # git is a Git object representing the main plaur repository
    def __init__(self, git):
        self.config = configparser.ConfigParser()
        self.git = git
        self.package_objects = {}

    def add(self, path, url, asdeps=False):
        # TODO: check that path is prefix-free to all the other paths
        self.config[path] = {
            'url' : url,
            'verified' : "",
            'asdeps' : asdeps,
        }

    def rm(self, path):
        if not path in self.config:
            raise UserErrorMessage("Invalid package path »%s«" % path)
        self.config.remove_section(path)

    def absolute_filepath(self):
        return os.path.join(self.git.work_tree(), plaur.main.config['packages_file'])
    def read(self):
        self.config.read(self.absolute_filepath())
    def write(self):
        with open(self.absolute_filepath(), 'w') as configfile:
            self.config.write(configfile)
            configfile.close()
    def query(self, path):
        return self.config[path]
    def paths(self):
        names = list(self.config.keys())
        names.remove('DEFAULT')
        return names

    def get_package(self,path):
        path = os.path.normpath(path)
        if not path in self.config:
            raise UserErrorMessage("Invalid package path »%s«" % path)
        elif path in self.package_objects:
            return self.package_objects[path]
        else:
            obj = plaur.package.Package(self,path)
            self.package_objects[path] = obj
            return obj

    def fetch(self, path):
        self.get_package(path).fetch()

    def __getitem__(self,key):
        return self.get_package(key)

    # commit the packages file (and all other staged changes) to the git
    def commit(self, message):
        self.git.call_success("add", self.absolute_filepath())
        self.git.call_success('commit', '-m', message);

    def compute_depgraph(self,paths,provide_guessing = False):
        # provide-guessing: assume that each directory provides a package with
        # the same name. (This only applies if the .SRCINFO does not exist)
        # for the following computation, only paths specified in the paths
        # parameter are considered.
        # this method returns a pair of dictionaries:
        # a dictionary that maps dependencies to the list of paths
        # which require that dependency
        dependencies = { }
        # similarly, a dictionary that maps package name to the list of
        # paths which provide that package name
        provides = { }
        for fullpath in paths:
            package = self[fullpath]
            try:
                for i in package.dependencies():
                    dependencies.setdefault(i,[]).append(package.path)
                for i in package.provides():
                    provides.setdefault(i,[]).append(package.path)
            except FileNotFoundError as e:
                debug("Can not open .SRCINFO of %s: %s" % (package.path, str(e)))
                if provide_guessing:
                    i = os.path.basename(package.path)
                    print("Guessing that %s provides %s" % (package.path, i))
                    provides.setdefault(i,[]).append(package.path)
        return (dependencies,provides)

    @staticmethod
    def depsort(dependencies,provides):
        # map dependencies/provides dicts as given in the compute_depgraph()
        # function to a concrete order of the involved paths.
        # for a path, it tells how many other paths need to be built before.
        in_degree = { }
        ready_to_build = queue.Queue() # paths that can be built immediately
        # if a multiple paths P1 and P2 both provide the same package required
        # by some other path B, then both P1 and P2 are built before B is.
        path_provides = { } # map paths to packages it provides
        for package,provided_by in provides.items():
            for path in provided_by:
                # path provides package
                in_degree[path] = 0;
                path_provides.setdefault(path, []).append(package)
        for dep,required_by in dependencies.items():
            for path in required_by:
                in_degree.setdefault(path, 0)
                in_degree[path] += len(provides.get(dep, []))
        for path,degree in in_degree.items():
            if degree == 0:
                ready_to_build.put(path)
        topsorted = [ ]
        while not ready_to_build.empty():
            path = ready_to_build.get(block = False)
            topsorted.append(path)
            for provs in path_provides[path]:
                for next_path in dependencies.get(provs, []):
                    in_degree[next_path] -= 1;
                    assert(in_degree[next_path] >= 0)
                    if (in_degree[next_path] <= 0):
                        ready_to_build.put(next_path)
        cyclic_deps = []
        for path,degree in in_degree.items():
            if degree > 0:
                cyclic_deps.append(path)
        if cyclic_deps:
            msg = "Ignoring packages because of cyclic dependencies: "
            msg += ' '.join(cyclic_deps)
            error_msg(msg)
        return topsorted

    @staticmethod
    def test_depsort():
        dependencies = {
            'libpurple' : [ 'someprotocolpath' ],
            'pidgin' : [ 'someprotocolpath' ],
            'glib' : [ 'fullpidgin' ],
        }
        provides = {
            'libpurple' : ['onlylibpurple', 'fullpidgin'],
            'pidgin' : [ 'fullpidgin'],
            'someprotocol' : [ 'someprotocolpath' ],
        }
        print (' '.join(PackageConfig.depsort(dependencies, provides)))
        dependencies = {
            'n1' : [ 'p1' ],
            'n2' : [ 'p1' ],
            'n3' : [ ],
        }
        provides = {
            'n1' : ['px', 'p2'],
            'n2' : [ 'fullpidgin'],
            'n3' : [ 'someprotocolpath', 'p1' ],
        }
        print (' '.join(PackageConfig.depsort(dependencies, provides)))
