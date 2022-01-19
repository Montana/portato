import os, logging

debug = logging.getLogger("portatoLogger").debug
info = logging.getLogger("portatoLogger").info
warning = logging.getLogger("portatoLogger").warning
error = logging.getLogger("portatoLogger").error
critical = logging.getLogger("portatoLogger").critical


def N_(s):
    return s


def get_runsystem():
    for sp in ("/etc/sabayon-release", "/etc/sabayon-edition"):
        if os.path.exists(sp):
            with open(sp) as r:
                return ("Sabayon", r.readline().strip())

    if os.path.exists("/etc/gentoo-release"):
        return ("Gentoo", "")

    else:
        return ("Unknown", "")


def paren_reduce(mystr):

    mylist = []
    while mystr:
        left_paren = mystr.find("(")
        has_left_paren = left_paren != -1
        right_paren = mystr.find(")")
        has_right_paren = right_paren != -1
        if not has_left_paren and not has_right_paren:
            freesec = mystr
            subsec = None
            tail = ""
        elif mystr[0] == ")":
            return [mylist, mystr[1:]]
        elif has_left_paren and not has_right_paren:
            error(_("Invalid dependency string"))
            return []
        elif has_left_paren and left_paren < right_paren:
            freesec, subsec = mystr.split("(", 1)
            subsec, tail = paren_reduce(subsec)
        else:
            subsec, tail = mystr.split(")", 1)
            subsec = [_f for _f in subsec.split(" ") if _f]
            return [mylist + subsec, tail]
        mystr = tail
        if freesec:
            mylist = mylist + [_f for _f in freesec.split(" ") if _f]
        if subsec is not None:
            mylist = mylist + [subsec]
    return mylist


def flatten(listOfLists):

    if not isinstance(listOfLists, list):
        return [listOfLists]

    ret = []
    for r in listOfLists:
        ret.extend(flatten(r))

    return ret


def detect_desktop_environment():

    desktop_environment = "generic"
    if os.environ.get("KDE_FULL_SESSION") == "true":
        desktop_environment = "kde"
    elif os.environ.get("GNOME_DESKTOP_SESSION_ID"):
        desktop_environment = "gnome"

    return desktop_environment
