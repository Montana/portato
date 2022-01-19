![64_64](https://user-images.githubusercontent.com/20936398/150125896-e8e94095-c383-40c6-a1e0-1729fce19612.png) **Portato**


Portato is a GUI for the package manager of Gentoo - Portage. Shoutout to @Necoro, the original creator of Portato.
Original depracated project: https://necoro.dev/portato/.

NB: _Current instructions are only good for when this version (v2022) is done and ready for deployment_.

## Why? 

The original author of Portato, @Necoro aka René Neumann, has stated "Portato does not work with current versions of portage. Hence I asked to remove it from Gentoo. I do not know, if I will ever make it work again. So please step up if you are interested in getting it running again." So I thought I'd be the person to get the new version of Portato going.

Before you install this, make sure you view your `environment variables` via:

```bash
emerge --info --verbose
```

Make sure your new locations are set:

```bash
repo_basedir="/var/db/repos"
repo_name="gentoo"
distdir="/var/cache/distfiles"
portdir="/var/db/repos/gentoo"
target_distdir="/var/cache/distfiles"
target_pkgdir="/var/cache/binpkgs"
```
Then run:

```bash
emerge --depclean
```

From this point onward, Portage might mention that certain updates are recommended to be executed. This is because system packages installed through the stage file might have newer versions available; Portage is now aware of new packages because of the repository snapshot. Package updates can be safely ignored for now; updates can be delayed until after the Gentoo installation has finished.

## Now what?

So, I'll take the request and have Portato back in the grips of Gentoo users hopefully **mid-to-late 2022.** You'll see under `REVISION` it says `2022`. I'm calling this `v2022` unless the author wants it called something else:

```python3
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
```

## TODO

* Update all Python to Python 3.9.
* Making sure it works with current development of Gentoo.
* Update the Portato GUI.
* Refactor existing code that can be salvaged to speed this along.
* Reorganize `imports`, and make a `requirements.txt`. 
* Symlink Portage with this version of Portato, (v2022). 
* Keep adding instructions as I go.

## Screenshots

![image](https://user-images.githubusercontent.com/20936398/150138840-95f019b7-db0a-4bfe-bfb7-05eb01c2f604.png)
