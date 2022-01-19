from future_builtins import map, filter, zip

import re
from threading import Lock

from .helper import debug, error

COMMENT = [";", "#"]

TRUE = re.compile("((true)|(1)|(on)|(wahr)|(ja)|(yes))", re.I)
FALSE = re.compile("((false)|(0)|(off)|(falsch)|(nein)|(no))", re.I)
SECTION = re.compile("\s*\[(?P<name>\w(\w|[-_])*)\]\s*")
EXPRESSION = re.compile(r"\s*(?P<key>\w(\w|[-_:])*)\s*=\s*(?P<value>.*)\s*")


class KeyNotFoundException(KeyError):
    pass


class SectionNotFoundException(KeyError):
    pass


class Value(object):
    def __init__(self, value, line, bool=None):

        self.__value = value
        self.line = line
        self.boolean = bool

        self.changed = False
        self.old = value

    def set(self, value):

        self.__value = value

        if value != self.old:
            self.changed = True
        else:
            self.changed = False

    def get(self):

        return self.__value

    def is_bool(self):

        return self.boolean != None

    def __str__(self):
        return str(self.__value)

    def __repr__(self):
        return self.__str__()

    value = property(get, set)


class ConfigParser:

    true_false = {
        "true": "false",
        "1": "0",
        "on": "off",
        "yes": "no",
        "ja": "nein",
        "wahr": "falsch",
    }
    true_false.update(list(zip(list(true_false.values()), list(true_false.keys()))))

    def __init__(self, file):
        self.file = file
        self.writelock = Lock()
        self.__initialize()

    def __initialize(self):

        self.vars = {"MAIN": {}}
        self.cache = []
        self.pos = {}
        self.sections = {"MAIN": -1}

    def _invert(self, val):

        return self.true_false[val.lower()]

    def parse(self):

        with open(self.file, "r") as f:
            self.cache = f.readlines()

        section = "MAIN"
        count = -1
        for line in self.cache:
            count += 1

            ls = line.strip()
            if not ls:
                continue  
            if ls[0] in COMMENT:
                continue  

            match = SECTION.search(line)
            if match:
                sec = match.group("name").upper()
                self.sections[sec] = count
                if sec != section:
                    self.vars[sec] = {}
                    section = sec
                continue

            match = EXPRESSION.search(line)
            if match:
                val = match.group("value")
                
                bool = None
                if TRUE.match(val):
                    bool = True
                elif FALSE.match(val):
                    bool = False

                key = match.group("key").lower()
                self.vars[section][key] = Value(val, count, bool=bool)
                self.pos[count] = match.span("value")
            else: 
                error(_("Unrecognized line in configuration: %s"), line)

    def _access(self, key, section):

        try:
            sectiondict = self.vars[section]
        except KeyError:
            raise SectionNotFoundException(
                "Section '%s' not found in file '%s'." % (section, self.file)
            )

        try:
            return sectiondict[key]
        except KeyError:
            raise KeyNotFoundException(
                "Key '%s' not found in section '%s' in file '%s'."
                % (key, section, self.file)
            )

    def get(self, key, section="MAIN"):

        section = section.upper()
        key = key.lower()
        return self._access(key, section).value

    def get_boolean(self, key, section="MAIN"):

        section = section.upper()
        key = key.lower()

        val = self._access(key, section)

        if val.is_bool():
            return val.boolean

        raise ValueError('"%s" is not a boolean. (%s)' % (key, val.value))

    def set(self, key, value, section="MAIN"):

        section = section.upper()
        key = key.lower()

        if not isinstance(value, bool): 
            self._access(key, section).value = value
        else:
            val = self._access(key, section)
            if val.is_bool():
                if value is not val.boolean:
                    val.boolean = value
                    val.value = self._invert(val.value)
            else:
                raise ValueError('"%s" is not a boolean.' % key)

    def add_section(self, section, comment=None, with_blankline=True):

        section = section.upper()

        if section in self.vars:
            return

        if with_blankline and len(self.cache) > 0:
            self.cache.append("\n")

        if comment:
            if isinstance(comment, str):
                comment = comment.split("\n")

            comment.insert(0, "")
            comment.append("")

            for c in comment:
                self.cache.append("# %s\n" % c)

        self.vars[section] = {}
        self.sections[section] = len(self.cache)
        self.cache.append("[%s]\n" % section)

    def add(self, key, value, section="MAIN", comment=None, with_blankline=True):

        section = section.upper()
        key = key.lower()

        try:
            if key in self.vars[section]:
                return self.set(key, value, section)
        except KeyError:
            raise SectionNotFoundException(
                "Section '%s' not found in file '%s'." % (section, self.file)
            )

        self.write()

        if self.vars[section]:
            mline = max((x.line for x in self.vars[section].values())) + 1
        else:
            mline = self.sections[section] + 1

        if with_blankline and mline > 0:
            self.cache.insert(mline, "\n")
            mline += 1

        if comment:
            if isinstance(comment, str):
                comment = comment.split("\n")

            for c in comment:
                self.cache.insert(mline, "; %s\n" % c)
                mline += 1

        self.cache.insert(mline, "%s = %s\n" % (key, value))

        self.write()

    def write(self):

        if not self.cache:
            return

        with self.writelock:
            for sec in self.vars.values():
                for val in sec.values():
                    if val.changed:
                        part1 = self.cache[val.line][: self.pos[val.line][0]]
                        part2 = val.value
                        part3 = self.cache[val.line][self.pos[val.line][1] :]

                        if not val.old and part1.endswith("\n"):
                            part1 = part1[:-1]
                            part3 = part3 + "\n"

                        self.cache[val.line] = part1 + part2 + part3

            with open(self.file, "w") as f:
                f.writelines(self.cache)

            self.__initialize()
            self.parse()
