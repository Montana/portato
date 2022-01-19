import os
from os.path import join as pjoin

if os.getuid() == 0:
    os.environ["HOME"] = "/root"

ROOT_DIR = ""
DATA_DIR = "./"

ICON_DIR = pjoin(ROOT_DIR, DATA_DIR, "icons/")
APP_ICON = pjoin(ICON_DIR, "portato-icon.png")

APP = "portato"
VERSION = "9999"
HOME = os.environ["HOME"]

CONFIG_DIR = pjoin(ROOT_DIR, "etc/")
CONFIG_LOCATION = pjoin(CONFIG_DIR, "portato.cfg")
SESSION_DIR = pjoin(os.environ["HOME"], ".portato")

LOCALE_DIR = "i18n/"
PLUGIN_DIR = pjoin(ROOT_DIR, DATA_DIR, "plugins/")
SETTINGS_DIR = pjoin(HOME, "." + APP)
TEMPLATE_DIR = "portato/gui/templates/"

REPOURI = "git://github.com/Montana/portato.git"
REVISION = "2022"
