![64_64](https://user-images.githubusercontent.com/20936398/150125896-e8e94095-c383-40c6-a1e0-1729fce19612.png) **Portato**


Portato is a GUI for the package manager of Gentoo - Portage. Shoutout to @Necoro, the original creator of Portato.
Original depracated project: https://necoro.dev/portato/.

NB: _Current instructions are only good for when this version (v2022) is done and ready for deployment_.

## Why? 

The author has stated "Portato does not work with current versions of portage. Hence I asked to remove it from Gentoo. I do not know, if I will ever make it work again. So please step up if you are interested in getting it running again."

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

So, I'll take the request and have Portato back in the grips of Gentoo users hopefully **mid-to-late 2022.**

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
