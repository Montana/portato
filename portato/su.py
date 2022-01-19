import os

from .constants import APP_ICON
from .helper import detect_desktop_environment


class SUCommand(object):
    def __init__(self, bin, args):
        self.bin = bin
        self.args = args

    def cmd(self, cmd):
        return [self.bin] + self.args + [cmd]

    def check(self):
        for p in os.environ["PATH"].split(":"):
            jp = os.path.join(p, self.bin)
            if os.access(jp, os.F_OK):
                return True

        return False


class SplitSUCommand(SUCommand):
    def cmd(self, cmd):
        return [self.bin] + self.args + cmd.split()


gtksu = SUCommand("gksu", ["-D", "Portato"])
kdesu = SUCommand("kdesu", ["-t", "-d", "-i", APP_ICON, "-c"])
ktsuss = SplitSUCommand("ktsuss", ["-m", "Portato"])


def detect_su_command():
    desktop_env = detect_desktop_environment()
    if desktop_env == "kde":
        sus = [kdesu, ktsuss, gtksu]
    elif desktop_env == "gnome":
        sus = [gtksu, ktsuss, kdesu]
    else:
        sus = [ktsuss, gtksu, kdesu]

    for s in sus:
        if s.check():
            return s

    return None
