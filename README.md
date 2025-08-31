![64_64](https://user-images.githubusercontent.com/20936398/150125896-e8e94095-c383-40c6-a1e0-1729fce19612.png) **Portato**


Portato is a GUI for the package manager of Gentoo - Portage. Shoutout to @Necoro, the original creator of Portato.
Original depracated project: https://necoro.dev/portato/.

<img width="544" height="559" alt="Screenshot 2025-08-29 at 5 27 26 AM" src="https://github.com/user-attachments/assets/72b8016a-4812-4d21-9025-d9e443dd4deb" />

NB: _Current instructions are only good for when this version (v2022) is done and ready for deployment_.

## Why? 

The original author of Portato, @Necoro aka René Neumann, has stated "Portato does not work with current versions of portage. Hence I asked to remove it from Gentoo. I do not know, if I will ever make it work again. So please step up if you are interested in getting it running again." So I thought I'd be the person to get the new version of Portato going.

As far as I know and have been informed, currently there's no plans of the original developer to bring it back on it's own. So I'm doing it. 

So first grab the Stage 3 as per usual pick the closest mirror: 

<img width="1259" height="500" alt="image" src="https://github.com/user-attachments/assets/81ad5c9a-6004-409a-873b-5cefbacb2b99" />

Thing to note, that altering USE flags in Gentoo frequently precipitates the inclusion of supplementary dependencies and necessitates subsequent package recompilations. On occasion, one must also reconcile antagonistic flags and dependency conflicts. Nevertheless, the process is less formidable than it may initially appear, as Gentoo furnishes predefined Portage profiles that establish canonical defaults for both global and per-package USE flags.

<img width="1536" height="1024" alt="gentooterm" src="https://github.com/user-attachments/assets/5ec5da15-c8a9-41a1-98d6-b4dda3286a28" />


## Rolling but no bleeding

Gentoo is a rolling distribution that priorities proven and stable software. If you’re looking for a rolling “bleeding edge” distribution you’re better suited with Arch or Void Linux.

I've built a tiny, modernized **CLI** placeholder for the old Portato GUI that lets you:
- show `emerge --info`
- search packages (`emerge -s`)
- list the world set
- install/remove packages (shells out to `emerge`)

This is **not** the full GTK GUI — it’s a stopgap that runs on Python 3 and current Gentoo, so you have *something usable today*. It’s structured so the GUI can be added back later (ideally via PyGObject/GTK3+).

## Quick install (pip)

```bash
python3 -m pip install --user .
# or editable for hacking:
python3 -m pip install --user -e .
```

Run it:

```bash
portato --help
portato info
portato search vim
portato world
# these require root/sudo, will shell out to emerge with -av for safety:
portato install app-editors/vim
portato remove app-editors/vim
```

## Local overlay install (ebuild)

Create a local overlay if you don't already have one (example path):
```bash
sudo mkdir -p /var/db/repos/localrepo
sudo tee /etc/portage/repos.conf/localrepo.conf >/dev/null <<'EOF'
[localrepo]
location = /var/db/repos/localrepo
masters = gentoo
auto-sync = no
EOF
```

Copy the ebuild & source tarball:
```bash
cd "/mnt/data/portato-almost-2025.08.29"
# make a source tarball Gentoo can digest
tar -C "/mnt/data/portato-almost-2025.08.29" -czf portato-almost-2025.08.29.tar.gz portato

sudo mkdir -p /var/db/repos/localrepo/app-portage/portato
sudo cp overlay/app-portage/portato/portato-2025.08.29.ebuild /var/db/repos/localrepo/app-portage/portato/
sudo cp portato-almost-2025.08.29.tar.gz /var/cache/distfiles/
```

Generate Manifest & emerge:
```bash
cd /var/db/repos/localrepo/app-portage/portato
sudo ebuild portato-2025.08.29.ebuild manifest
sudo emerge -av app-portage/portato
```

## Next steps (GUI revival checklist)

- Port the legacy GUI to **GTK3** using **PyGObject** (`dev-python/pygobject`).
- Replace obsolete `pynotify` with `notify2` or GLib notifications via `gi.repository`.
- Replace `optparse` with `argparse`.
- Replace any `future_builtins`, `ConfigParser`, `UserDict` etc. with Python 3 equivalents.
- Re-implement IPC as needed (GLib main loop or dbus/async queue). For now, the CLI runs without IPC.
- Package with `pyproject.toml` and `distutils-r1` / `python-single-r1` in the ebuild.
- Add a `portato.gui` package and wire it under the same CLI entrypoint.

---

**Included:** a simple ebuild (`overlay/app-portage/portato/portato-2025.08.29.ebuild`) targeting Python 3.11/3.12.


## GUI (GTK3) preview
This bundle includes a very simple GTK3 GUI (PyGObject) with:
- Search box (`emerge -s`) and results table
- Buttons: **Pretend**, **Install**, **Remove**, **Info**
- A **World** tab to show your world set
- An **Output** pane that streams command output

### Requirements
```bash
emerge -av dev-python/pygobject
# (optional but helpful for privileged commands in a terminal)
emerge -av x11-terms/xterm
```

### Run the GUI
```bash
portato gui
```

**Notes about privileged actions:** The GUI will try to run install/remove using:
1) `pkexec emerge ...` if available, else
2) `xterm -e sudo emerge ...` if available, else
3) it will show the exact command so you can run it in a terminal.

This avoids freezing the UI and keeps things safe and explicit.

### Known Limitations
- This is **not** the original Portato feature-parity yet (no queueing, advanced sets UI, etc.).
- We currently shell out to `emerge` for search/install/remove. We can add Portage API calls next.
- If `gentoolkit` is installed, future versions can use `equery` to enrich details.


## Added Portato-like features
- **Results table** with double-click to queue
- **Queue** (install/remove), pretend and apply
- **World** viewer and editor
- **USE flags** writer to `/etc/portage/package.use/portato`
- **News** viewer via `eselect news`
- **Logs** viewer for `/var/log/emerge.log`

This mirrors core workflows of legacy Portato while staying Python 3 + GTK3.


## Extra features
- **Emerge options**: --deep, --newuse, --oneshot, --keep-going, --jobs N
- **Installed** tab (needs gentoolkit or portage-utils)
- **Keywords / Mask** tab to write to `/etc/portage/package.accept_keywords/portato`, `/etc/portage/package.mask/portato`, `/etc/portage/package.unmask/portato`
- **Repos** tab to sync overlays (`emerge --sync` or `emaint sync -a`)


## New: Details sidebar (Portage-like)
- Shows **Description, Homepage, License, Keywords** (Portage API if available; fallback to `equery meta` / `emerge -s`).
- Displays **IUSE flags** as checkboxes with current enable/disable status (parsed from `emerge -pv`).
- **Save** button writes your selections to `/etc/portage/package.use/portato` (overwrites prior line for that atom).
- **Dependency Tree** button runs `emerge -ptv <atom>` into the Output pane.


## Polished toward classic Portato
- **Queue persistence** across sessions (`~/.config/portato/queue.json`).
- **Settings persistence** for emerge options, jobs, API toggle (`~/.config/portato/settings.json`).
- **Clickable Homepage** in Details (opens in browser).
- **Graphical Dependency Tree** tab: parses `emerge -ptv` indentation into a tree view.

## Author 
Michael Mendy (c) 2025.
