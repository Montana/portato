import os
import itertools as itt
from subprocess import Popen, PIPE # This is for grep. - Montana.

from . import system, is_package
from ..helper import debug, error, warning

CONFIG = {
    "usefile": "portato",
    "maskfile": "portato",
    "testingfile": "portato",
    "usePerVersion": True,
    "maskPerVersion": True,
    "testingPerVersion": True,
}


class Constants:
    def __init__(self):
        self.clear()

    def clear(self):
        self._use_path = None
        self._mask_path = None
        self._unmask_path = None
        self._testing_path = None
        self._use_path_is_dir = None
        self._mask_path_is_dir = None
        self._unmask_path_is_dir = None
        self._testing_path_is_dir = None

    def __get(self, name, path):
        if self.__dict__[name] is None:
            self.__dict__[name] = os.path.join(system.get_config_path(), path)

        return self.__dict__[name]

    def __is_dir(self, path):
        name = "_" + path + "_is_dir"
        if self.__dict__[name] is None:
            self.__dict__[name] = os.path.isdir(self.__class__.__dict__[path](self))
        return self.__dict__[name]

    def use_path(self):
        return self.__get("_use_path", "package.use")

    def use_path_is_dir(self):
        return self.__is_dir("use_path")

    def mask_path(self):
        return self.__get("_mask_path", "package.mask")

    def mask_path_is_dir(self):
        return self.__is_dir("mask_path")

    def unmask_path(self):
        return self.__get("_unmask_path", "package.unmask")

    def unmask_path_is_dir(self):
        return self.__is_dir("unmask_path")

    def testing_path(self):
        return self.__get("_testing_path", "package.keywords")

    def testing_path_is_dir(self):
        return self.__is_dir("testing_path")


CONST = Constants()


def grep(pkg, path):

    if not is_package(pkg):
        pkg = system.new_package(pkg)  

    if os.path.exists(path):
        command = "egrep -x -n -r -H '^[<>!=~]{0,2}%s(-[0-9].*)?[[:space:]]?.*$' %s"  
        return (
            Popen((command % (pkg.get_cp(), path)), shell=True, stdout=PIPE)
            .communicate()[0]
            .splitlines()
        )
    else:
        return []


def get_data(pkg, path):

    flags = []

    for line in grep(pkg, path):
        file, line, fl = line.split(":", 2) 
        fl = fl.split()
        crit = fl[0]
        fl = fl[1:]

        nc = itt.takewhile(lambda x: x[0] != "#", fl)
        flags.append((file, line, crit, list(nc)))

    return flags


def set_config(cfg):

    for i in CONFIG.keys():
        if not i in cfg:
            raise KeyError("Missing keyword in config: " + i)

    for i in CONFIG:
        CONFIG[i] = cfg[i]


def generate_path(cpv, exp):

    if exp.find("$(") != -1:
        cat, pkg, ver, rev = system.split_cpv(cpv)
        if rev != "r0":
            ver = "%s-%s" % (ver, rev)

        exp = (
            exp.replace("$(cat)", cat)
            .replace("$(pkg)", pkg)
            .replace("$(cat-1)", cat.split("-")[0])
            .replace("$(version)", ver)
        )

        try:
            exp = exp.replace("$(cat-2)", cat.split("-")[1])
        except IndexError: 
            pass

    return exp


useFlags = {}  #
newUseFlags = {}


def invert_use_flag(flag):

    if flag[0] == "-":
        return flag[1:]
    else:
        return "-" + flag


def sort_use_flag_list(flaglist):
    def flag_key(flag):
        if flag[0] in "+-":
            return flag[1:]
        else:
            return flag

    flaglist.sort(key=flag_key)
    return flaglist


def filter_defaults(flaglist):

    for flag in flaglist:
        if flag[0] in "+-":
            yield flag[1:]
        else:
            yield flag


def set_use_flag(pkg, flag):

    global useFlags, newUseFlags

    if not is_package(pkg):
        pkg = system.new_package(pkg)

    cpv = pkg.get_cpv()
    invFlag = invert_use_flag(flag)

    data = None
    if not cpv in useFlags:
        data = get_data(pkg, CONST.use_path())
        useFlags[cpv] = data
    else:
        data = useFlags[cpv]

    if not cpv in newUseFlags:
        newUseFlags[cpv] = []

    debug("data: %s", str(data))
    added = False
    for file, line, crit, flags in data:
        if pkg.matches(crit):
            if (
                invFlag in flags
                or (file, line, invFlag, False) in newUseFlags[cpv]
                or (file, line, flag, True) in newUseFlags[cpv]
            ):
                if added:
                    del newUseFlags[cpv][-1]
                added = True
                jumpOut = False
                for t in ((file, line, invFlag, False), (file, line, flag, True)):
                    if t in newUseFlags[cpv]:
                        newUseFlags[cpv].remove(t)
                        jumpOut = True

                if not jumpOut:
                    newUseFlags[cpv].append((file, line, invFlag, True))

                    if invFlag in pkg.get_actual_use_flags():
                        newUseFlags[cpv].append((file, line, flag, False))
                break

            elif flag in flags:
                added = True
                break

            else:
                if not added:
                    newUseFlags[cpv].append((file, line, flag, False))
                added = True

    if not added:
        path = CONST.use_path()
        if CONST.use_path_is_dir():
            path = os.path.join(CONST.use_path(), generate_path(cpv, CONFIG["usefile"]))
        try:
            newUseFlags[cpv].remove((path, -1, invFlag, False))
        except ValueError:  # not in UseFlags
            newUseFlags[cpv].append((path, -1, flag, False))

    newUseFlags[cpv] = list(set(newUseFlags[cpv]))
    debug("newUseFlags: %s", str(newUseFlags))


def remove_new_use_flags(cpv):

    if is_package(cpv):
        cpv = cpv.get_cpv()

    try:
        del newUseFlags[cpv]
    except KeyError:
        pass


def get_new_use_flags(cpv):

    if is_package(cpv):
        cpv = cpv.get_cpv()

    list2return = set()
    try:
        for file, line, flag, remove in newUseFlags[cpv]:
            if remove:
                list2return.add("~" + invert_use_flag(flag))
            else:
                list2return.add(flag)
    except KeyError:
        pass

    return list(list2return)


def write_use_flags():

    global newUseFlags, useFlags

    def combine(list):
        return " ".join(list) + "\n"

    def insert(flag, list):
        list.insert(1, flag)

    def remove(flag, list):
        list.remove(flag)

        if len(list) == 1 or list[1][0] == "#":
            list[0] = "#" + list[0]
            list.append("#removed by portato#")

    file_cache = {}
    for cpv in newUseFlags:
        flagsToAdd = []

        newUseFlags[cpv].sort(key=lambda x: x[3])  #
        for file, line, flag, delete in newUseFlags[cpv]:
            line = int(line)

            if line == -1:
                flagsToAdd.append(flag)

            else:
                if not file in file_cache:
                    with open(file, "r") as f:
                        lines = []
                        i = 1
                        while i < line:
                            lines.append(f.readline())
                            i += 1
                        l = f.readline().split()

                        if delete:
                            remove(flag, l)
                        else:
                            insert(flag, l)
                        lines.append(combine(l))

                        lines.extend(f.readlines())

                        file_cache[file] = lines

                else:
                    l = file_cache[file][line - 1].split()
                    if delete:
                        remove(flag, l)
                    else:
                        insert(flag, l)
                    file_cache[file][line - 1] = combine(l)

        if flagsToAdd:

            msg = "\n#portato update#\n"
            comb = combine(flagsToAdd)
            if CONFIG["usePerVersion"]:
                msg += "=%s %s" % (cpv, comb)
            else:
                list = system.split_cpv(cpv)
                msg += "%s/%s %s" % (list[0], list[1], comb)

            if not file in file_cache:
                with open(file, "a") as f:
                    f.write(msg)
            else:
                file_cache[file].append(msg)

    for file in file_cache:
        with open(file, "w") as f:
            f.writelines(file_cache[file])

    useFlags = {}
    newUseFlags = {}
    system.reload_settings()


new_masked = {}
new_unmasked = {}


def set_masked(pkg, masked=True):

    global new_masked, newunmasked

    if not is_package(pkg):
        pkg = system.new_package(pkg)

    cpv = pkg.get_cpv()

    if not cpv in new_unmasked:
        new_unmasked[cpv] = []
    if not cpv in new_masked:
        new_masked[cpv] = []

    if masked:
        link_neq = new_masked
        link_eq = new_unmasked
        path = CONST.unmask_path()
    else:
        link_neq = new_unmasked
        link_eq = new_masked
        path = CONST.mask_path()

    copy = link_eq[cpv][:]
    for file, line in copy:
        if line == "-1":
            link_eq[cpv].remove((file, line))

    copy = link_neq[cpv][:]
    for file, line in copy:
        if line != "-1":
            link_neq[cpv].remove((file, line))

    if masked == pkg.is_masked():
        return

    data = get_data(pkg, path)
    debug("data: %s", str(data))
    done = False
    for file, line, crit, flags in data:
        if pkg.matches(crit):
            link_eq[cpv].append((file, line))
            done = True

    if done:
        return

    if masked:
        is_dir = CONST.mask_path_is_dir()
        path = CONST.mask_path()
    else:
        is_dir = CONST.unmask_path_is_dir()
        path = CONST.unmask_path()

    if is_dir:
        file = os.path.join(path, generate_path(cpv, CONFIG["maskfile"]))
    else:
        file = path

    link_neq[cpv].append((file, "-1"))
    link_neq[cpv] = list(set(link_neq[cpv]))
    debug("new_(un)masked: %s", str(link_neq))


def remove_new_masked(cpv):
    if is_package(cpv):
        cpv = cpv.get_cpv()

    try:
        del new_masked[cpv]
    except KeyError:
        pass

    try:
        del new_unmasked[cpv]
    except KeyError:
        pass


def new_masking_status(cpv):
    if is_package(cpv):
        cpv = cpv.get_cpv()

    def get(list):
        ret = None
        if cpv in list and list[cpv] != []:
            for file, line in list[cpv]:
                _ret = int(line) == -1
                if ret is not None and _ret != ret:
                    error(_("Conflicting values for masking status: %s"), list)
                else:
                    ret = _ret
        return ret

    masked = get(new_masked)
    if masked is None:
        masked = get(new_unmasked)
        if masked is not None:
            masked = not masked

    if masked is not None:
        if masked:
            return "masked"
        else:
            return "unmasked"
    else:
        return None


def is_locally_masked(pkg, changes=True):

    if not is_package(pkg):
        pkg = system.new_package(pkg)

    if changes:
        if new_masking_status(pkg) == "masked":

            if pkg.get_cpv() in new_unmasked:
                if new_unmasked[pkg.get_cpv()]:
                    return False

            return True

        if new_masking_status(pkg) == "unmasked":
            return False

    list = get_data(pkg, CONST.mask_path())

    if not list:
        return False

    for file, line, crit, fl in list:
        if pkg.matches(crit):
            return True

    return False


def write_masked():
    global new_unmasked, new_masked
    file_cache = {}

    def write(cpv, file, line):
        line = int(line)

        if line == -1:
            msg = "\n#portato update#\n"
            if CONFIG["maskPerVersion"]:
                msg += "=%s\n" % cpv
            else:
                list = system.split_cpv(cpv)
                msg += "%s/%s\n" % (list[0], list[1])
            if not file in file_cache:
                with open(file, "a") as f:
                    f.write(msg)
            else:
                file_cache[file].append(msg)
        else:
            if not file in file_cache:
                with open(file, "r") as f:
                    lines = []
                    i = 1
                    while i < line:
                        lines.append(f.readline())
                        i = i + 1
                    l = f.readline()
                    l = "#" + l[:-1] + " # removed by portato\n"
                    lines.append(l)

                    lines.extend(f.readlines())

                    file_cache[file] = lines
                l = file_cache[file][line - 1]
                l = "#" + l[:-1] + " # removed by portato\n"
                file_cache[file][line - 1] = l

    for cpv in new_masked:
        for file, line in new_masked[cpv]:
            write(cpv, file, line)

    for cpv in new_unmasked:
        for file, line in new_unmasked[cpv]:
            write(cpv, file, line)

    for file in file_cache.keys():
        f = open(file, "w")
        f.writelines(file_cache[file])
        f.close()
    new_masked = {}
    new_unmasked = {}
    system.reload_settings()


newTesting = {}
arch = ""


def remove_new_testing(cpv):
    if is_package(cpv):
        cpv = cpv.get_cpv()

    try:
        del newTesting[cpv]
    except KeyError:
        pass


def new_testing_status(cpv):
    if is_package(cpv):
        cpv = cpv.get_cpv()

    if cpv in newTesting:
        for file, line in newTesting[cpv]:
            if line == "-1":
                return False
            else:
                return True

    return None


def set_testing(pkg, enable):

    global arch, newTesting
    if not is_package(pkg):
        pkg = system.new_package(pkg)

    arch = pkg.get_global_settings("ARCH")
    cpv = pkg.get_cpv()
    if not cpv in newTesting:
        newTesting[cpv] = []

    for file, line in newTesting[cpv][:]:
        if (enable and line != "-1") or (not enable and line == "-1"):
            newTesting[cpv].remove((file, line))

    if (enable and not pkg.is_testing()) or (not enable and pkg.is_testing()):
        return

    if not enable:
        test = get_data(pkg, CONST.testing_path())
        debug("data (test): %s", str(test))
        for file, line, crit, flags in test:
            try:
                flagMatches = flags[0] == "~" + arch
            except IndexError:  # no flags
                warning(
                    _("Line %(line)s in file %(file)s misses a keyword (e.g. '~x86')."),
                    {"line": line, "file": file},
                )
                debug("No keyword. Assuming match.")
                flagMatches = True

            if pkg.matches(crit) and flagMatches:
                newTesting[cpv].append((file, line))
    else:
        if CONST.testing_path_is_dir():
            file = os.path.join(
                CONST.testing_path(), generate_path(cpv, CONFIG["testingfile"])
            )
        else:
            file = CONST.testing_path()
        newTesting[cpv].append((file, "-1"))

    newTesting[cpv] = list(set(newTesting[cpv]))
    debug("newTesting: %s", str(newTesting))


def write_testing():
    global arch, newTesting
    file_cache = {}

    for cpv in newTesting:
        for file, line in newTesting[cpv]:
            line = int(line)
            if line == -1:
                msg = "\n#portato update#\n"
                if CONFIG["testingPerVersion"]:
                    msg += "=%s ~%s\n" % (cpv, arch)
                else:
                    list = system.split_cpv(cpv)
                    msg += "%s/%s ~%s\n" % (list[0], list[1], arch)
                if not file in file_cache:
                    with open(file, "a") as f:
                        f.write(msg)
                else:
                    file_cache[file].append(msg)
            else:
                if not file in file_cache:

                    with open(file, "r") as f:
                        lines = []
                        i = 1
                        while i < line:
                            lines.append(f.readline())
                            i = i + 1

                        l = f.readline()
                        l = "#" + l[:-1] + " # removed by portato\n"
                        lines.append(l)

                        lines.extend(f.readlines())

                        file_cache[file] = lines
                else:
                    l = file_cache[file][line - 1]
                    l = "#" + l[:-1] + " # removed by portato\n"
                    file_cache[file][line - 1] = l

    for file in file_cache.keys():
        with open(file, "w") as f:
            f.writelines(file_cache[file])
    newTesting = {}
    system.reload_settings()
