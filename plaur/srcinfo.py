
"""parse a .SRCINFO file and provide some wrapper functions"""

import re
from plaur.utils import UserErrorMessage

class SRCINFO:
    def __init__(self, filepath):
        self.filepath = filepath
        # sections is a dictionary that maps pairs (e.g. ("pkgname","plaur")) to
        # section dictionaries. Each section dictionary maps keys to a list of
        # values
        # TODO: keep the order of sections fix if their order matters in the
        #       .SRCINFO specification
        self.sections = { }
        self.loaded_once = False

    def load(self):
        if not self.loaded_once:
            self.reload()
            self.loaded_once = True

    def reload(self):
        self.sections = { }
        with open(self.filepath, 'r') as f:
            lines = f.readlines()
        is_emptyline = re.compile('^[ \\t]*(#.*)?$')
        is_header = re.compile('^(?P<name>[^= \\t]+) = (?P<value>.*)$')
        is_option = re.compile('^\t(?P<name>[^= \\t]+) = (?P<value>.*)$')
        current_section = { }
        current_header = None
        class Holder(object):
            def set(self, v):
                self.v = v
                return v
            def get(self):
                return self.v
        h = Holder()
        for i, line in enumerate(lines):
            line = line.rstrip('\r\n')
            if (is_emptyline.match(line)):
                #print("%d SKIP %s" % (i,line))
                continue
            elif h.set(is_header.match(line)):
                #print("%d header %s" %(i,line))
                if current_header != None:
                    self.sections[current_header] = current_section
                current_header = (h.get().group('name'),h.get().group('value'))
                current_section = { }
            elif h.set(is_option.match(line)):
                name = h.get().group('name')
                if not name in current_section:
                    current_section[name] = [ ]
                current_section[name].append(h.get().group('value'))
            else:
                raise UserErrorMessage("Line %d: unrecognized syntax: \"%s\"" % (i+1, line))
        # save the last section
        if current_header != None:
            self.sections[current_header] = current_section
        #print(self.sections)
    # example usage:
    # SRCINFO('.SRCINFO').reload()

    def __str__(self):
        buf = ""
        for (sectype,secname),section in self.sections.items():
            buf += "%s = %s\n" % (sectype,secname)
            for key,values in section.items():
                for v in values:
                    buf += "\t%s = %s\n" % (key,v)
            buf += "\n"
        return buf

    def packages(self):
        for sectype,secname in self.sections:
            if sectype == "pkgname":
                yield secname

    def query_pkgname(self,pkgname,key):
        # TODO: look up the precise semantics of .SRCINFO
        value = []
        fallback_value = []
        for (sectype,secname),options in self.sections.items():
            if sectype == "pkgname" and secname == pkgname:
                if key in options:
                    value += options[key]
            if sectype == "pkgbase":
                if key in options:
                    fallback_value += options[key]
        if value == []:
            value = fallback_value
        return value

    def package_names(self):
        class PackageName:
            def __init__(self,name,ver,rel,arch):
                self.name = name
                self.ver = ver
                self.rel = rel
                self.arch = arch
                self.suffix = '.pkg.tar.xz'
            def __str__(self):
                pattern = [self.name, self.ver, self.rel, self.arch]
                return '-'.join(pattern) + self.suffix
        res = [ ]
        for name in self.packages():
            ver = self.query_pkgname(name,'pkgver')[0]
            rel = self.query_pkgname(name,'pkgrel')[0]
            arches = self.query_pkgname(name,'arch')
            default_arch = 'x86_64'
            arch = 'any' if 'any' in arches else default_arch
            res.append(PackageName(name,ver,rel,arch))
        return res

    def query_any(self,key):
        value = []
        for (sectype,secname),options in self.sections.items():
            if key in options:
                value += options[key]
        return value

    @staticmethod
    def drop_version_constraints(deplist):
        """From a list of dependencies, drop all the versioning constraints,
        resulting in a traversable object of package names
        """
        only_name = re.compile('^[^<>=]*')
        for i in deplist:
            yield only_name.search(i).group(0)

