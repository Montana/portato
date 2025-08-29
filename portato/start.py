import argparse, os, subprocess, sys, shlex, textwrap, pathlib

def _run(cmd, check=False):
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        return p.returncode, p.stdout
    except FileNotFoundError as e:
        return 127, f"{e}\n"

def _print_box(title, body):
    print("="*len(title))
    print(title)
    print("="*len(title))
    print(body.rstrip())
    print()

def cmd_info(_args):
    rc, out = _run(["emerge", "--info"])
    if rc != 0:
        out = "Could not run 'emerge --info'. Are you on Gentoo?\n\n" + out
    _print_box("emerge --info", out)

def cmd_search(args):
    if not args.atom:
        print("Usage: portato search <atom>")
        return 2
    rc, out = _run(["emerge", "-s", args.atom])
    _print_box(f"Search: {args.atom}", out)
    return rc

def _world_path():
    # default world path
    candidates = ["/var/lib/portage/world", "/var/lib/portage/world_sets"]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]

def cmd_world(_args):
    p = _world_path()
    if not os.path.exists(p):
        print(f"No world file found at {p}.")
        return 1
    with open(p) as f:
        data = f.read().strip()
    _print_box(f"World set @ {p}", data or "(empty)")

def _sudo_prefix():
    # only prefix with sudo if not root
    return [] if os.geteuid() == 0 else ["sudo"]

def cmd_install(args):
    if not args.atom:
        print("Usage: portato install <atom>")
        return 2
    cmd = _sudo_prefix() + ["emerge", "-av", args.atom]
    print("->", " ".join(shlex.quote(c) for c in cmd))
    os.execvp(cmd[0], cmd)

def cmd_remove(args):
    if not args.atom:
        print("Usage: portato remove <atom>")
        return 2
    cmd = _sudo_prefix() + ["emerge", "-avC", args.atom]
    print("->", " ".join(shlex.quote(c) for c in cmd))
    os.execvp(cmd[0], cmd)

def main(argv=None):
    argv = argv or sys.argv[1:]
    p = argparse.ArgumentParser(prog="portato", description="Portato (Almost): a small Gentoo Portage helper")
    sub = p.add_subparsers(dest="cmd")

    s_info = sub.add_parser("info", help="Show emerge --info")
    s_info.set_defaults(func=cmd_info)

    s_search = sub.add_parser("search", help="Search packages via emerge -s")
    s_search.add_argument("atom", nargs="?")
    s_search.set_defaults(func=cmd_search)

    s_world = sub.add_parser("world", help="Show world set")
    s_world.set_defaults(func=cmd_world)

    s_install = sub.add_parser("install", help="Install a package (shells out to emerge -av)")
    s_install.add_argument("atom", nargs="?")
    s_install.set_defaults(func=cmd_install)

    s_remove = sub.add_parser("remove", help="Remove a package (shells out to emerge -avC)")
    s_remove.add_argument("atom", nargs="?")
    s_remove.set_defaults(func=cmd_remove)

    s_gui = sub.add_parser("gui", help="Launch GTK3 GUI (preview)")
    s_gui.set_defaults(func=cmd_gui)

    if not argv:
        p.print_help()
        return 0

    args = p.parse_args(argv)
    if not hasattr(args, "func"):
        p.print_help()
        return 2

    return args.func(args) or 0

if __name__ == "__main__":
    raise SystemExit(main())


def cmd_gui(_args):
    try:
        from .gui import run_gui
    except Exception as e:
        print("GUI dependencies missing? Try: emerge -av dev-python/pygobject")
        print(e)
        return 1
    return run_gui()
