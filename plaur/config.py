
import configparser
import os

plaur_ini = "plaur.ini" # filename of the central plaur configuration file

class PlaurConfig:
    def __init__(self,filename = None):
        self.file = configparser.ConfigParser()
        self.file.add_section('options')
        self.filename = filename
        self.defaults = {
            # the defaults dictionary maps keys to pairs of default values and
            # some description
            'packages_file': ("packages.ini",
                  "file path to packages config, relative to the plaur git root"),
        }
    def set_filename_from_git(self, git):
        global plaur_ini
        self.filename = os.path.join(git.git_work_tree, plaur_ini)
        self.read()

    # this function should return a read-only reference...
    def __getitem__(self,key):
        if key in self.file['options']:
            return self.file['options']['key']
        elif key in self.defaults:
            (v,_) = self.defaults[key]
            return v
        else:
            return None

    def read(self):
        self.file.read(self.filename)
    def write(self):
        with open(self.filename, 'w') as configfile:
            self.file.write(configfile)
            configfile.close()
    def print_contents(self):
        print("Available options:")
        for (k,(_,d)) in self.defaults.items():
            print("%s: %s" % (k,d))
        print("\nDefault values:")
        for (k,(v,_)) in self.defaults.items():
            print("%s = %s" % (k,v))
        print("\nContents of " + str(self.filename) + ":")
        for s in self.file.sections():
            print("[%s]" % s)
            for k,v in self.file.items(s):
                print("%s = %s" % (k,v))
