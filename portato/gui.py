import os, shlex, subprocess, threading, time, io
from gi.repository import Gtk, GLib
import json

# -------------------- helpers --------------------
# -------------------- config/persist helpers --------------------
def _cfg_dir():
    d = os.path.join(os.path.expanduser("~"), ".config", "portato")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d

def _cfg_path(name):
    return os.path.join(_cfg_dir(), name)

def save_json(name, obj):
    try:
        with open(_cfg_path(name), "w") as f:
            json.dump(obj, f, indent=2, sort_keys=True)
    except Exception:
        pass

def load_json(name):
    try:
        with open(_cfg_path(name)) as f:
            return json.load(f)
    except Exception:
        return None

def _run_stream(cmd, line_cb, done_cb):
    def worker():
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in iter(p.stdout.readline, ""):
                GLib.idle_add(line_cb, line.rstrip("\n"))
            p.wait()
            GLib.idle_add(done_cb, p.returncode)
        except FileNotFoundError as e:
            GLib.idle_add(line_cb, str(e))
            GLib.idle_add(done_cb, 127)
    threading.Thread(target=worker, daemon=True).start()

def _run_capture(cmd):
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        return p.returncode, p.stdout
    except FileNotFoundError as e:
        return 127, str(e)

def _has(cmd):
    return subprocess.call(["which", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0

# -------------------- models ---------------------
class OutputPane:
    def __init__(self):
        self.buf = Gtk.TextBuffer()
        self.view = Gtk.TextView(buffer=self.buf)
        self.view.set_editable(False)
        self.view.set_monospace(True)

    def widget(self):
        sc = Gtk.ScrolledWindow()
        sc.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sc.add(self.view)
        return sc

    def clear(self):
        self.buf.set_text("")

    def append(self, text):
        end = self.buf.get_end_iter()
        self.buf.insert(end, text + "\n")

class QueueModel(Gtk.ListStore):
    def __init__(self):
        super().__init__(str, str)   # atom, action

class SearchModel(Gtk.ListStore):
    def __init__(self):
        super().__init__(str, str, str, str)  # atom, installed, version, description

class InstalledModel(Gtk.ListStore):
    def __init__(self):
        super().__init__(str, str)  # atom, version

# -------------------- details widget -------------
class DetailsWidget(Gtk.Box):
    """
    Shows rich package details and per-flag checkboxes.
    Uses Portage Python API if available, else equery/meta or emerge -pv.
    """
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        self.atom = None
        self.meta = {}      # homepage, license, description, keywords
        self.flags = []     # [(flag, enabled_bool, description)]
        self.target_flags = {}  # desired state after toggles

        # header with atom
        self.lbl_atom = Gtk.Label()
        self.lbl_atom.set_xalign(0)

        grid = Gtk.Grid(column_spacing=12, row_spacing=6)
        row = 0
        grid.attach(Gtk.Label(label="Atom:", xalign=0), 0, row, 1, 1)
        grid.attach(self.lbl_atom, 1, row, 1, 1); row += 1

        self.lbl_desc = Gtk.Label(xalign=0, wrap=True)
        grid.attach(Gtk.Label(label="Description:", xalign=0), 0, row, 1, 1)
        grid.attach(self.lbl_desc, 1, row, 1, 1); row += 1

        self.lbl_home = Gtk.LinkButton.new_with_label("", "")
        self.lbl_home.set_alignment(0.0, 0.5)
        grid.attach(Gtk.Label(label="Homepage:", xalign=0), 0, row, 1, 1)
        grid.attach(self.lbl_home, 1, row, 1, 1); row += 1

        self.lbl_lic = Gtk.Label(xalign=0, wrap=True)
        grid.attach(Gtk.Label(label="License:", xalign=0), 0, row, 1, 1)
        grid.attach(self.lbl_lic, 1, row, 1, 1); row += 1

        self.lbl_kw = Gtk.Label(xalign=0, wrap=True)
        grid.attach(Gtk.Label(label="Keywords:", xalign=0), 0, row, 1, 1)
        grid.attach(self.lbl_kw, 1, row, 1, 1); row += 1

        # IUSE flags area (scrolled)
        self.flag_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        sc = Gtk.ScrolledWindow()
        sc.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sc.set_min_content_height(180)
        sc.add(self.flag_box)

        self.btn_depgraph = Gtk.Button(label="Show Dependency Tree (pretend)")
        self.btn_depgraph.connect("clicked", self.on_depgraph)

        # Buttons for applying flags
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.btn_save_flags = Gtk.Button(label="Save USE to package.use/portato")
        self.btn_save_flags.connect("clicked", self.on_save_flags)
        self.btn_reset_flags = Gtk.Button(label="Reset")
        self.btn_reset_flags.connect("clicked", self.on_reset_flags)
        btn_box.pack_start(self.btn_save_flags, False, False, 0)
        btn_box.pack_start(self.btn_reset_flags, False, False, 0)

        self.pack_start(grid, False, False, 0)
        self.pack_start(Gtk.Label(label="IUSE flags:"), False, False, 0)
        self.pack_start(sc, True, True, 0)
        self.pack_start(self.btn_depgraph, False, False, 0)
        self.pack_start(btn_box, False, False, 0)

        self.output_cb = None  # set by parent to append to output
        self.priv_cb = None    # set by parent to run privileged command
        self.status_cb = None  # set by parent to set status

    def set_callbacks(self, output_append, run_priv, set_status):
        self.output_cb = output_append
        self.priv_cb = run_priv
        self.status_cb = set_status

    def _append_output(self, text):
        if self.output_cb:
            self.output_cb(text)

    def _set_status(self, text):
        if self.status_cb:
            self.status_cb(text)

    # -------- public API --------
    def load_atom(self, atom):
        self.atom = atom
        self.lbl_atom.set_text(atom)
        self.flag_box.foreach(lambda w: self.flag_box.remove(w))  # clear
        self.meta = self._fetch_meta(atom)
        self.flags = self._fetch_flags(atom)

        self.lbl_desc.set_text(self.meta.get("description",""))
        home = (self.meta.get("homepage","") or "").split()[0]
        try:
            self.lbl_home.set_uri(home if home else "")
            self.lbl_home.set_label(home if home else "")
        except Exception:
            pass
        self.lbl_lic.set_text(self.meta.get("license",""))
        self.lbl_kw.set_text(self.meta.get("keywords",""))

        # checkboxes
        self.target_flags = {}
        for flag, enabled, desc in self.flags:
            hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            cb = Gtk.CheckButton.new_with_label(flag + (f" — {desc}" if desc else ""))
            cb.set_active(bool(enabled))
            cb.connect("toggled", self._on_toggle_flag, flag)
            hb.pack_start(cb, False, False, 0)
            self.flag_box.pack_start(hb, False, False, 0)
            self.target_flags[flag] = bool(enabled)
        self.flag_box.show_all()

    # -------- actions ----------
    def on_depgraph(self, _btn):
        if not self.atom:
            return
        cmd = ["emerge", "-ptv", self.atom]
        self._set_status(" ".join(shlex.quote(a) for a in cmd))
        # capture once to build tree
        rc, out = _run_capture(cmd)
        self._append_output(out)
        self._set_status(f"Depgraph done (rc={rc})")
        # build tree from indentation
        try:
            self._build_dep_tree(out)
        except Exception:
            pass

    def on_save_flags(self, _btn):
        if not self.atom or not self.target_flags:
            return
        # Build flags string like: "flag1 -flag2 ..."
        parts = []
        for f, enabled in sorted(self.target_flags.items()):
            parts.append(f if enabled else f"-{f}")
        script = (
            "set -e; "
            "sudo mkdir -p /etc/portage/package.use; "
            "grep -v '^{atom} ' /etc/portage/package.use/portato 2>/dev/null > /tmp/portato.use.$$ || true; "
            "echo {atom} {flags} >> /tmp/portato.use.$$; "
            "sudo mv /tmp/portato.use.$$ /etc/portage/package.use/portato"
        ).format(atom=shlex.quote(self.atom), flags=shlex.quote(" ".join(parts)))
        if self.priv_cb:
            self.priv_cb(["bash", "-lc", script])

    def on_reset_flags(self, _btn):
        if self.atom:
            self.load_atom(self.atom)

    def _on_toggle_flag(self, widget, flag):
        self.target_flags[flag] = widget.get_active()

    # -------- data fetching -----
    def _fetch_meta(self, atom):
        # Try Portage API
        try:
            import portage
            portdb = portage.db["/"]["porttree"].dbapi
            matches = portdb.match(atom)
            meta = {}
            if matches:
                cpv = matches[-1]  # choose 'latest'
                fields = ["DESCRIPTION","HOMEPAGE","LICENSE","KEYWORDS","IUSE"]
                data = dict(zip(fields, portdb.aux_get(cpv, fields)))
                meta = {
                    "description": data.get("DESCRIPTION",""),
                    "homepage": data.get("HOMEPAGE",""),
                    "license": data.get("LICENSE",""),
                    "keywords": data.get("KEYWORDS",""),
                    "iuse_raw": data.get("IUSE",""),
                }
                return meta
        except Exception:
            pass

        # Fallback: equery meta
        meta = {"description":"", "homepage":"", "license":"", "keywords":""}
        if _has("equery"):
            rc, out = _run_capture(["equery", "meta", atom])
            for ln in out.splitlines():
                low = ln.lower()
                if low.startswith("description"):
                    meta["description"] = ln.split(":",1)[1].strip()
                elif low.startswith("homepage"):
                    meta["homepage"] = ln.split(":",1)[1].strip()
                elif low.startswith("license"):
                    meta["license"] = ln.split(":",1)[1].strip()
                elif low.startswith("keywords"):
                    meta["keywords"] = ln.split(":",1)[1].strip()
        else:
            # Try emerge -s description line
            rc, out = _run_capture(["emerge", "-s", atom])
            desc = ""
            for ln in out.splitlines():
                if "Description" in ln:
                    desc = ln.split(":",1)[1].strip()
                    break
            meta["description"] = desc
        return meta

    def _build_dep_tree(self, text):
        # naive indent-based parser for emerge -ptv
        lines = [ln.rstrip('\n') for ln in text.splitlines()]
        stack = []
        # Inform parent to clear and use its dep tree store
        parent = self.get_parent()
        # walk up to PortatoGUI to access store
        win = None
        w = self
        while w is not None:
            if isinstance(w, Gtk.Window):
                win = w
                break
            w = w.get_parent()
        if not win or not hasattr(win, 'deptree_store'):
            return
        store = win.deptree_store
        store.clear()
        for ln in lines:
            if not ln.strip():
                continue
            # count leading spaces
            indent = len(ln) - len(ln.lstrip(' '))
            text = ln.strip()
            node = store.append(None if indent==0 else stack[-1][1], [text]) if not stack else None
            while stack and indent <= stack[-1][0]:
                stack.pop()
            parent_iter = stack[-1][1] if stack else None
            cur = store.append(parent_iter, [text])
            stack.append((indent, cur))

    def _fetch_flags(self, atom):
        # Prefer Portage API for IUSE list + pretend for status
        flags = []
        iuse = []
        try:
            import portage
            portdb = portage.db["/"]["porttree"].dbapi
            matches = portdb.match(atom)
            if matches:
                cpv = matches[-1]
                iuse_raw = portdb.aux_get(cpv, ["IUSE"])[0]
                iuse = [f.lstrip("+-") for f in iuse_raw.split() if f]
        except Exception:
            pass

        enabled = set()
        disabled = set()
        # Determine status via emerge -pv (parsing USE="...")
        rc, out = _run_capture(["emerge", "-pv", atom])
        for ln in out.splitlines():
            if 'USE="' in ln:
                q = ln.split('USE="',1)[1]
                q = q.split('"',1)[0]
                for tok in q.split():
                    if tok.startswith("-"):
                        disabled.add(tok[1:])
                    else:
                        enabled.add(tok)
                break

        if not iuse:
            # Try equery uses to get the flag list
            if _has("equery"):
                rc, out = _run_capture(["equery", "uses", atom])
                # equery uses prints lines with +/- and flag, capture the flag token
                for ln in out.splitlines():
                    ls = ln.strip()
                    if not ls:
                        continue
                    # Example formats vary; try splitting
                    parts = ls.replace("[", " ").replace("]", " ").split()
                    # Find a token that looks like a flag (letters, numbers, + - _)
                    f = None
                    for p in parts:
                        if p and p not in ("+", "-", "+-", "-+", "(-)", "(+)"):
                            # heuristic: flags don't contain ":" or "/"
                            if ":" not in p and "/" not in p:
                                f = p
                                break
                    if f:
                        iuse.append(f)

        # Build final list (flag, bool, desc(empty))
        seen = set()
        for f in sorted(set(iuse) | enabled | disabled):
            if f in seen:
                continue
            seen.add(f)
            flags.append((f, (f in enabled), ""))
        return flags

# -------------------- main GUI --------------------
class PortatoGUI(Gtk.Window):
    def __init__(self):
        super().__init__(title="Portato (Almost)")
        self.set_default_size(1280, 800)

        self.output = OutputPane()
        self.queue = QueueModel()
        self.search_model = SearchModel()
        self.installed_model = InstalledModel()
        self.details = DetailsWidget()
        self.details.set_callbacks(self.output.append, self._run_privileged, self._set_status)

        # Emerge options
        self.opt_deep = Gtk.CheckButton(label="--deep")
        self.opt_newuse = Gtk.CheckButton(label="--newuse")
        self.opt_oneshot = Gtk.CheckButton(label="--oneshot")
        self.opt_keepgoing = Gtk.CheckButton(label="--keep-going")
        self.opt_jobs = Gtk.SpinButton.new_with_range(0, 64, 1)
        self.opt_jobs.set_value(0)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(outer)

        # Header bar
        hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Search atom (e.g., app-editors/vim)")
        btn_search = Gtk.Button(label="Search")
        btn_search.connect("clicked", self.on_search)
        btn_pretend = Gtk.Button(label="Pretend")
        btn_pretend.connect("clicked", self.on_pretend)
        btn_apply = Gtk.Button(label="Apply Queue")
        btn_apply.connect("clicked", self.on_apply_queue)
        btn_info = Gtk.Button(label="Info")
        btn_info.connect("clicked", self.on_info)
        for w in [self.search_entry, btn_search, btn_pretend, btn_apply, btn_info]:
            hb.pack_start(w, False if w is not self.search_entry else True, True, 0)
        outer.pack_start(hb, False, False, 0)

        # Options bar
        ob = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        for w in [self.opt_deep, self.opt_newuse, self.opt_oneshot, self.opt_keepgoing, Gtk.Label(label="--jobs"), self.opt_jobs]:
            ob.pack_start(w, False, False, 0)
        outer.pack_start(ob, False, False, 0)
        # persist option changes
        for w in [self.opt_deep, self.opt_newuse, self.opt_oneshot, self.opt_keepgoing, self.opt_jobs, self.opt_api]:
            try:
                w.connect("toggled" if hasattr(w, 'connect') else "value-changed", lambda *_: self._save_settings())
            except Exception:
                pass


        # Main paned: left (tabs) / right (details+output)
        paned = Gtk.Paned()
        outer.pack_start(paned, True, True, 0)

        # Left notebook
        nb = Gtk.Notebook()
        paned.add1(nb)

        # Results tab
        self.results_tree = Gtk.TreeView(model=self.search_model)
        columns = [("Atom", 0, 320), ("Installed", 1, 90), ("Version", 2, 120), ("Description", 3, 520)]
        for title, colid, width in columns:
            renderer = Gtk.CellRendererText()
            col = Gtk.TreeViewColumn(title, renderer, text=colid)
            col.set_resizable(True)
            col.set_min_width(width)
            self.results_tree.append_column(col)
        self.results_tree.connect("cursor-changed", self.on_results_select)
        self.results_tree.connect("row-activated", self.on_results_activate)
        nb.append_page(self._scrolled(self.results_tree), Gtk.Label(label="Results"))

        # Installed tab
        self.inst_tree = Gtk.TreeView(model=self.installed_model)
        for title, colid, width in [("Atom", 0, 480), ("Version", 1, 120)]:
            renderer = Gtk.CellRendererText()
            col = Gtk.TreeViewColumn(title, renderer, text=colid)
            col.set_resizable(True)
            col.set_min_width(width)
            self.inst_tree.append_column(col)
        btn_inst_refresh = Gtk.Button(label="Refresh Installed")
        btn_inst_refresh.connect("clicked", self.on_installed_refresh)
        inst_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        inst_box.pack_start(self._scrolled(self.inst_tree), True, True, 0)
        inst_box.pack_start(btn_inst_refresh, False, False, 0)
        nb.append_page(inst_box, Gtk.Label(label="Installed"))

        # Queue tab
        self.queue_tree = Gtk.TreeView(model=self.queue)
        qcols = [("Atom", 0, 480), ("Action", 1, 120)]
        for title, colid, width in qcols:
            renderer = Gtk.CellRendererText()
            col = Gtk.TreeViewColumn(title, renderer, text=colid)
            col.set_resizable(True)
            col.set_min_width(width)
            self.queue_tree.append_column(col)
        queue_btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_q_install = Gtk.Button(label="Add Install")
        btn_q_install.connect("clicked", self.on_queue_add_install)
        btn_q_remove = Gtk.Button(label="Add Remove")
        btn_q_remove.connect("clicked", self.on_queue_add_remove)
        btn_q_del = Gtk.Button(label="Delete Selected")
        btn_q_del.connect("clicked", self.on_queue_delete)
        for b in [btn_q_install, btn_q_remove, btn_q_del]:
            queue_btns.pack_start(b, False, False, 0)
        queue_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        queue_box.pack_start(self._scrolled(self.queue_tree), True, True, 0)
        queue_box.pack_start(queue_btns, False, False, 0)
        nb.append_page(queue_box, Gtk.Label(label="Queue"))

        # World tab
        self.world_buf = Gtk.TextBuffer()
        self.world_view = Gtk.TextView(buffer=self.world_buf)
        self.world_view.set_editable(False)
        self.world_view.set_monospace(True)
        world_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        world_box.pack_start(self._scrolled(self.world_view), True, True, 0)
        world_btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_world_refresh = Gtk.Button(label="Refresh World")
        btn_world_refresh.connect("clicked", self.on_world_refresh)
        btn_world_add = Gtk.Button(label="Add to World from selection")
        btn_world_add.connect("clicked", self.on_world_add_from_sel)
        btn_world_remove = Gtk.Button(label="Remove from World (input)")
        btn_world_remove.connect("clicked", self.on_world_remove_input)
        self.world_entry = Gtk.Entry()
        self.world_entry.set_placeholder_text("app-cat/pkg to remove")
        for w in [btn_world_refresh, btn_world_add, self.world_entry, btn_world_remove]:
            world_btns.pack_start(w, False, False, 0)
        world_box.pack_start(world_btns, False, False, 0)
        nb.append_page(world_box, Gtk.Label(label="World"))

        # USE Flags tab (text-based fallback still present)
        self.use_atom_entry = Gtk.Entry()
        self.use_atom_entry.set_placeholder_text("Atom (e.g., app-editors/vim)")
        self.use_flags_entry = Gtk.Entry()
        self.use_flags_entry.set_placeholder_text("Flags (e.g., python -ruby)")
        btn_apply_use = Gtk.Button(label="Apply USE → /etc/portage/package.use/portato")
        btn_apply_use.connect("clicked", self.on_apply_use_flags)
        use_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        use_controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        for w in [self.use_atom_entry, self.use_flags_entry, btn_apply_use]:
            use_controls.pack_start(w, False, False, 0)
        self.use_buf = Gtk.TextBuffer()
        use_view = Gtk.TextView(buffer=self.use_buf)
        use_view.set_editable(False)
        use_view.set_monospace(True)
        use_box.pack_start(use_controls, False, False, 0)
        use_box.pack_start(self._scrolled(use_view), True, True, 0)
        nb.append_page(use_box, Gtk.Label(label="USE Flags (manual)"))

        # Keywords / Mask tab
        self.kw_atom_entry = Gtk.Entry()
        self.kw_atom_entry.set_placeholder_text("Atom for keyword/mask")
        self.kw_keywords_entry = Gtk.Entry()
        self.kw_keywords_entry.set_placeholder_text("Keywords (e.g., ~amd64 or ** for live)")
        btn_apply_kw = Gtk.Button(label="Apply Keywords → package.accept_keywords/portato")
        btn_apply_kw.connect("clicked", self.on_apply_keywords)
        self.mask_atom_entry = Gtk.Entry()
        self.mask_atom_entry.set_placeholder_text("Atom to mask/unmask")
        btn_mask = Gtk.Button(label="Mask → package.mask/portato")
        btn_mask.connect("clicked", self.on_apply_mask)
        btn_unmask = Gtk.Button(label="Unmask → package.unmask/portato")
        btn_unmask.connect("clicked", self.on_apply_unmask)
        kw_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        kw_controls1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        for w in [self.kw_atom_entry, self.kw_keywords_entry, btn_apply_kw]:
            kw_controls1.pack_start(w, False, False, 0)
        kw_controls2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        for w in [self.mask_atom_entry, btn_mask, btn_unmask]:
            kw_controls2.pack_start(w, False, False, 0)
        self.kw_buf = Gtk.TextBuffer()
        kw_view = Gtk.TextView(buffer=self.kw_buf)
        kw_view.set_editable(False)
        kw_view.set_monospace(True)
        kw_box.pack_start(kw_controls1, False, False, 0)
        kw_box.pack_start(kw_controls2, False, False, 0)
        kw_box.pack_start(self._scrolled(kw_view), True, True, 0)
        nb.append_page(kw_box, Gtk.Label(label="Keywords / Mask"))

        # News tab
        self.news_buf = Gtk.TextBuffer()
        news_view = Gtk.TextView(buffer=self.news_buf)
        news_view.set_editable(False)
        news_view.set_monospace(True)
        news_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        btn_news_refresh = Gtk.Button(label="Refresh News")
        btn_news_refresh.connect("clicked", self.on_news_refresh)
        news_box.pack_start(btn_news_refresh, False, False, 0)
        news_box.pack_start(self._scrolled(news_view), True, True, 0)
        nb.append_page(news_box, Gtk.Label(label="News"))

        # Logs tab
        self.logs_buf = Gtk.TextBuffer()
        logs_view = Gtk.TextView(buffer=self.logs_buf)
        logs_view.set_editable(False)
        logs_view.set_monospace(True)
        logs_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        btn_logs_refresh = Gtk.Button(label="Refresh emerge.log")
        btn_logs_refresh.connect("clicked", self.on_logs_refresh)
        logs_box.pack_start(btn_logs_refresh, False, False, 0)
        logs_box.pack_start(self._scrolled(logs_view), True, True, 0)
        nb.append_page(logs_box, Gtk.Label(label="Logs"))

        # Repos tab
        repo_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        btn_sync = Gtk.Button(label="Sync (emerge --sync)")
        btn_sync.connect("clicked", self.on_sync)
        btn_emaint = Gtk.Button(label="emaint sync -a")
        btn_emaint.connect("clicked", self.on_emaint_sync)
        repo_box.pack_start(btn_sync, False, False, 0)
        repo_box.pack_start(btn_emaint, False, False, 0)
        nb.append_page(repo_box, Gtk.Label(label="Repos"))

        # Right side: details + output as a notebook
        right = Gtk.Notebook()
        right.append_page(self.details, Gtk.Label(label="Details"))
        self.deptree_store = Gtk.TreeStore(str)
        self.deptree_view = Gtk.TreeView(model=self.deptree_store)
        renderer = Gtk.CellRendererText(); col = Gtk.TreeViewColumn("Dependency", renderer, text=0)
        self.deptree_view.append_column(col)
        right.append_page(self.details, Gtk.Label(label="Details"))
        right.append_page(self.output.widget(), Gtk.Label(label="Output"))
        right.append_page(self._scrolled(self.deptree_view), Gtk.Label(label="Dep Tree"))
        paned.add2(right)

        # status bar
        self.status = Gtk.Statusbar()
        self.status.push(0, "Ready")
        outer.pack_start(self.status, False, False, 0)

        self.connect("destroy", Gtk.main_quit)
        self.on_world_refresh(None)
        self.on_installed_refresh(None)
        self.on_news_refresh(None)
        self.on_logs_refresh(None)
        # Load persisted queue and settings
        try:
            self._load_persisted_queue()
        except Exception:
            pass
        try:
            self._load_settings()
        except Exception:
            pass


    # -------------- utilities --------------
    def _scrolled(self, widget):
        sc = Gtk.ScrolledWindow()
        sc.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sc.add(widget)
        return sc

    def _set_status(self, msg):
        self.status.push(0, msg)

    def build_emerge_opts(self):
        opts = []
        if self.opt_deep.get_active():
            opts.append("--deep")
        if self.opt_newuse.get_active():
            opts.append("--newuse")
        if self.opt_oneshot.get_active():
            opts.append("--oneshot")
        if self.opt_keepgoing.get_active():
            opts.append("--keep-going")
        jobs = int(self.opt_jobs.get_value())
        if jobs > 0:
            opts.extend(["--jobs", str(jobs)])
        return opts

    def _run_privileged(self, args):
        if _has("pkexec"):
            cmd = ["pkexec"] + args
            self.output.clear()
            self._set_status(" ".join(shlex.quote(a) for a in cmd))
            _run_stream(cmd, self.output.append, lambda rc: self._set_status(f"Done (rc={rc})"))
            return
        if _has("xterm"):
            cmd = ["xterm", "-e", "sudo"] + args
            self.output.append("Launching terminal: " + " ".join(shlex.quote(a) for a in cmd))
            subprocess.Popen(cmd)
            self._set_status("Terminal launched")
            return
        self.output.append("Run manually:\n  sudo " + " ".join(shlex.quote(a) for a in args))
        self._set_status("Displayed command for manual execution")

    # -------------- events -----------------
    def on_results_select(self, _tree):
        atom = self._selected_search_atom()
        if atom:
            self.details.load_atom(atom)

    def on_results_activate(self, tree, path, col):
        it = self.search_model.get_iter(path)
        atom = self.search_model.get_value(it, 0)
        self.queue.append([atom, "install"])
        self._persist_queue()
        self._set_status(f"Queued {atom} for install")
        self.details.load_atom(atom)

    def on_search(self, _btn):
        atom = self.search_entry.get_text().strip()
        if not atom:
            self._set_status("Enter search text")
            return
        self.search_model.clear()
        self._set_status(f"Searching {atom} ...")
        if _has("equery"):
            rc, out = _run_capture(["equery", "list", "-po", atom])
            entries = [l.strip() for l in out.splitlines() if l.strip()]
            for e in entries[:800]:
                e_clean = e.split()[-1]
                desc = ""
                rc2, out2 = _run_capture(["equery", "meta", "-d", e_clean])
                for ln in out2.splitlines():
                    if ln.lower().startswith("description"):
                        desc = ln.split(":",1)[1].strip()
                        break
                inst = "yes" if e.startswith("I ") else "no"
                self.search_model.append([e_clean, inst, "", desc])
        else:
            rc, out = _run_capture(["emerge", "-s", atom])
            atom_line = ""
            desc = ""
            for ln in out.splitlines():
                if ln.startswith(" "):
                    if "Description" in ln:
                        desc = ln.split(":",1)[1].strip()
                elif "/" in ln and ln.strip().startswith("*")==False:
                    atom_line = ln.strip()
                    parts = atom_line.split()
                    if parts:
                        namever = parts[0].rstrip(":")
                        if "-" in namever and "/" in namever:
                            pkg = namever.split("/",1)[0] + "/" + "-".join(namever.split("/",1)[1].split("-")[:-1])
                            ver = namever.split("-",1)[1] if "-" in namever.split("/",1)[1] else ""
                        else:
                            pkg, ver = namever, ""
                        installed = "yes" if "[ Installed " in ln else "no"
                        self.search_model.append([pkg, installed, ver, desc])
                        desc = ""
        self._set_status("Search done")

    def on_info(self, _btn):
        self.output.clear()
        self._set_status("Running emerge --info ...")
        _run_stream(["emerge", "--info"], self.output.append, lambda rc: self._set_status(f"Info done (rc={rc})"))

    def on_installed_refresh(self, _btn):
        self.installed_model.clear()
        if _has("equery"):
            rc, out = _run_capture(["equery", "list", "-i", "*"])
            for ln in out.splitlines():
                s = ln.strip()
                if s and "/" in s:
                    self.installed_model.append([s, ""])
        elif _has("qlist"):
            rc, out = _run_capture(["qlist", "-I"])
            for ln in out.splitlines():
                s = ln.strip()
                if s and "/" in s:
                    self.installed_model.append([s, ""])
        else:
            self.installed_model.append(["(install gentoolkit or portage-utils for installed list)", ""])

    def on_queue_add_install(self, _btn):
        atom = self._selected_search_atom()
        if atom:
            self.queue.append([atom, "install"])
        self._persist_queue()

    def on_queue_add_remove(self, _btn):
        atom = self._selected_search_atom()
        if atom:
            self.queue.append([atom, "remove"])
        self._persist_queue()

    def on_queue_delete(self, _btn):
        sel = self.queue_tree.get_selection()
        model, itr = sel.get_selected()
        if itr:
            model.remove(itr)
            self._persist_queue()

    def on_pretend(self, _btn):
        atoms = []
        for atom, action in self._queue_rows():
            atoms.append(atom if action == "install" else f"--unmerge {atom}")
        if not atoms:
            it = self._selected_search_atom()
            if it:
                atoms = [it]
        if not atoms:
            self._set_status("Nothing to pretend")
            return
        cmd = ["emerge", "-pv"] + self.build_emerge_opts() + atoms
        self.output.clear()
        self._set_status(" ".join(shlex.quote(a) for a in cmd))
        _run_stream(cmd, self.output.append, lambda rc: self._set_status(f"Pretend done (rc={rc})"))

    def on_apply_queue(self, _btn):
        install_atoms = [a for a, act in self._queue_rows() if act == "install"]
        remove_atoms  = [a for a, act in self._queue_rows() if act == "remove"]
        if not install_atoms and not remove_atoms:
            self._set_status("Queue is empty")
            return
        if install_atoms:
            self._run_privileged(["emerge", "-av"] + self.build_emerge_opts() + install_atoms)
        if remove_atoms:
            self._run_privileged(["emerge", "-avC"] + remove_atoms)
        self._persist_queue()

    def _queue_rows(self):
        rows = []
        itr = self.queue.get_iter_first()
        while itr:
            rows.append([self.queue.get_value(itr, 0), self.queue.get_value(itr, 1)])
            itr = self.queue.iter_next(itr)
        return rows

    def _selected_search_atom(self):
        sel = self.results_tree.get_selection()
        model, itr = sel.get_selected()
        if itr:
            return model.get_value(itr, 0)
        return None

    def on_world_refresh(self, _btn):
        p = self._world_path()
        if os.path.exists(p):
            with open(p) as f:
                self.world_buf.set_text(f.read())
            self._set_status(f"World loaded from {p}")
        else:
            self.world_buf.set_text("(no world file found)")
            self._set_status("World missing")

    def on_world_add_from_sel(self, _btn):
        atom = self._selected_search_atom()
        if not atom:
            self._set_status("Select a package in Results")
            return
        self._run_privileged(["bash", "-lc", f"echo {shlex.quote(atom)} | sudo tee -a {shlex.quote(self._world_path())}"])

    def on_world_remove_input(self, _btn):
        atom = self.world_entry.get_text().strip()
        if not atom:
            self._set_status("Enter an atom to remove")
            return
        script = f"grep -vxF {shlex.quote(atom)} {shlex.quote(self._world_path())} > /tmp/.world.$$ && sudo mv /tmp/.world.$$ {shlex.quote(self._world_path())}"
        self._run_privileged(["bash", "-lc", script])

    def _world_path(self):
        for p in ["/var/lib/portage/world", "/var/lib/portage/world_sets"]:
            if os.path.exists(p):
                return p
        return "/var/lib/portage/world"

    def on_apply_use_flags(self, _btn):
        atom = self.use_atom_entry.get_text().strip()
        flags = self.use_flags_entry.get_text().strip()
        if not atom or not flags:
            self._set_status("Provide atom and flags")
            return
        script = (
            "set -e; "
            "sudo mkdir -p /etc/portage/package.use; "
            "echo {atom} {flags} | sudo tee -a /etc/portage/package.use/portato"
        ).format(atom=shlex.quote(atom), flags=shlex.quote(flags))
        self._run_privileged(["bash", "-lc", script])

    def on_apply_keywords(self, _btn):
        atom = self.kw_atom_entry.get_text().strip()
        kw = self.kw_keywords_entry.get_text().strip()
        if not atom or not kw:
            self._set_status("Provide atom and keywords")
            return
        script = (
            "set -e; "
            "sudo mkdir -p /etc/portage/package.accept_keywords; "
            "echo {atom} {kw} | sudo tee -a /etc/portage/package.accept_keywords/portato"
        ).format(atom=shlex.quote(atom), kw=shlex.quote(kw))
        self._run_privileged(["bash", "-lc", script])

    def on_apply_mask(self, _btn):
        atom = self.mask_atom_entry.get_text().strip()
        if not atom:
            self._set_status("Provide atom to mask")
            return
        script = (
            "set -e; "
            "sudo mkdir -p /etc/portage/package.mask; "
            "echo {atom} | sudo tee -a /etc/portage/package.mask/portato"
        ).format(atom=shlex.quote(atom))
        self._run_privileged(["bash", "-lc", script])

    def on_apply_unmask(self, _btn):
        atom = self.mask_atom_entry.get_text().strip()
        if not atom:
            self._set_status("Provide atom to unmask")
            return
        script = (
            "set -e; "
            "sudo mkdir -p /etc/portage/package.unmask; "
            "echo {atom} | sudo tee -a /etc/portage/package.unmask/portato"
        ).format(atom=shlex.quote(atom))
        self._run_privileged(["bash", "-lc", script])

    def on_news_refresh(self, _btn):
        if _has("eselect"):
            rc, out = _run_capture(["eselect", "news", "list"])
            self.news_buf.set_text(out)
        else:
            self.news_buf.set_text("eselect not found")

    def on_logs_refresh(self, _btn):
        p = "/var/log/emerge.log"
        if os.path.exists(p):
            try:
                with io.open(p, 'r', encoding='utf-8', errors='replace') as f:
                    data = "".join(f.readlines()[-1000:])
                self.logs_buf.set_text(data)
            except Exception as e:
                self.logs_buf.set_text(str(e))
        else:
            self.logs_buf.set_text("(no /var/log/emerge.log)")

    def on_sync(self, _btn):
        self._run_privileged(["emerge", "--sync"])

    def on_emaint_sync(self, _btn):
        self._run_privileged(["emaint", "sync", "-a"])

    def on_profiles_refresh(self, _btn):
        rc, out = _run_capture(["eselect", "profile", "list"]) if _has("eselect") else (1, "eselect not found")
        self.prof_buf.set_text(out)

    def on_profile_set(self, _btn):
        target = self.prof_entry.get_text().strip()
        if not target:
            self._set_status("Enter profile number or path")
            return
        if target.isdigit():
            self._run_privileged(["eselect", "profile", "set", target])
        else:
            # set symlink directly
            script = "set -e; sudo ln -snf {target} /etc/portage/make.profile".format(target=shlex.quote(target))
            self._run_privileged(["bash", "-lc", script])
        self._notify("Portato", "Profile set requested")

    def _repos_dir(self):
        return "/etc/portage/repos.conf"

    def _portato_conf(self):
        return os.path.join(self._repos_dir(), "portato.conf")

    def on_overlays_refresh(self, _btn):
        lines = []
        d = self._repos_dir()
        if os.path.isdir(d):
            for fn in sorted(os.listdir(d)):
                p = os.path.join(d, fn)
                try:
                    with open(p) as f:
                        lines.append(f"##### {p} #####")
                        lines.extend([ln.rstrip("\\n") for ln in f])
                        lines.append("")
                except Exception as e:
                    lines.append(f"<<error reading {p}: {e}>>")
        else:
            lines.append("(no /etc/portage/repos.conf directory)")
        self.ov_buf.set_text("\\n".join(lines))

    def on_overlay_add(self, _btn):
        name = self.ov_name.get_text().strip()
        sync = self.ov_syncuri.get_text().strip()
        loc  = self.ov_location.get_text().strip()
        if not (name and sync and loc):
            self._set_status("Provide name, sync-uri, location")
            return
        content = f"[{name}]\\nlocation = {loc}\\nsync-type = git\\nsync-uri = {sync}\\npriority = 50\\n"
        script = (
            "set -e; "
            "sudo mkdir -p {d}; "
            "if [ -f {f} ]; then "
            "awk 'BEGIN{{p=1}} /^\\[/{{p=1}} $0==\"[{name}]\"{{p=0}} p{{print}}' {f} > /tmp/portato.repos.$$; "
            "mv /tmp/portato.repos.$$ {f}; "
            "fi; "
            "printf '%s' {here} | sudo tee -a {f} >/dev/null"
        ).format(d=shlex.quote(self._repos_dir()), f=shlex.quote(self._portato_conf()),
                 name=name, here=shlex.quote(content))
        self._run_privileged(["bash", "-lc", script])
        self._notify("Portato", f"Overlay {name} added/updated")

    def on_overlay_remove(self, _btn):
        name = self.ov_name.get_text().strip()
        if not name:
            self._set_status("Provide overlay name")
            return
        script = (
            "set -e; "
            "if [ -f {f} ]; then "
            "awk 'BEGIN{{skip=0}} /^\\[/{{skip=0}} $0==\"[{name}]\"{{skip=1}} !skip{{print}}' {f} > /tmp/portato.repos.$$ && sudo mv /tmp/portato.repos.$$ {f}; "
            "fi"
        ).format(f=shlex.quote(self._portato_conf()), name=name)
        self._run_privileged(["bash", "-lc", script])
        self._notify("Portato", f"Overlay {name} removed from portato.conf")

    # -------- Settings (binpkg) --------
    def on_settings_refresh(self, _btn):
        # naive scan of /etc/portage/make.conf and make.conf.d/ for values
        features = ""; opts = ""; binhost = ""
        paths = ["/etc/portage/make.conf"]
        d = "/etc/portage/make.conf.d"
        if os.path.isdir(d):
            for fn in sorted(os.listdir(d)):
                if fn.endswith(".conf"):
                    paths.append(os.path.join(d, fn))
        for p in paths:
            try:
                with open(p) as f:
                    for ln in f:
                        ls = ln.strip()
                        if ls.startswith("FEATURES=") and not features:
                            features = ls.split("=",1)[1].strip().strip('"\\'+"'"+'')
                        elif ls.startswith("EMERGE_DEFAULT_OPTS=") and not opts:
                            opts = ls.split("=",1)[1].strip().strip('"\\'+"'"+'')
                        elif ls.startswith("PORTAGE_BINHOST=") and not binhost:
                            binhost = ls.split("=",1)[1].strip().strip('"\\'+"'"+'')
            except Exception:
                pass
        self.chk_buildpkg.set_active("buildpkg" in features)
        self.chk_usepkg.set_active("getbinpkg" in opts or "--getbinpkg" in opts or "--usepkg" in opts)
        self.binhost_entry.set_text(binhost)

    def on_settings_save(self, _btn):
        feats = "buildpkg binpkg-multi-instance" if self.chk_buildpkg.get_active() else ""
        opts  = "--getbinpkg --usepkg --binpkg-respect-use=y" if self.chk_usepkg.get_active() else ""
        binhost = self.binhost_entry.get_text().strip()
        parts = []
        if feats: parts.append(f'FEATURES="{feats}"')
        if opts:  parts.append(f'EMERGE_DEFAULT_OPTS="{opts}"')
        if binhost: parts.append(f'PORTAGE_BINHOST="{binhost}"')
        content = "\\n".join(parts) + "\\n"
        script = (
            "set -e; "
            "sudo mkdir -p /etc/portage/make.conf.d; "
            "printf '%s' {here} | sudo tee /etc/portage/make.conf.d/portato.conf >/dev/null"
        ).format(here=shlex.quote(content))
        self._run_privileged(["bash", "-lc", script])
        self._notify("Portato", "Saved binpkg settings")


    def _persist_queue(self):
        rows = [{"atom": a, "action": act} for a, act in self._queue_rows()]
        save_json("queue.json", rows)

    def _load_persisted_queue(self):
        rows = load_json("queue.json") or []
        self.queue.clear()
        for r in rows:
            self.queue.append([r.get("atom",""), r.get("action","install")])

    def _save_settings(self):
        data = {
            "deep": self.opt_deep.get_active(),
            "newuse": self.opt_newuse.get_active(),
            "oneshot": self.opt_oneshot.get_active(),
            "keepgoing": self.opt_keepgoing.get_active(),
            "jobs": int(self.opt_jobs.get_value()),
            "api": self.opt_api.get_active()
        }
        save_json("settings.json", data)

    def _load_settings(self):
        data = load_json("settings.json") or {}
        self.opt_deep.set_active(bool(data.get("deep", False)))
        self.opt_newuse.set_active(bool(data.get("newuse", False)))
        self.opt_oneshot.set_active(bool(data.get("oneshot", False)))
        self.opt_keepgoing.set_active(bool(data.get("keepgoing", False)))
        try:
            self.opt_jobs.set_value(int(data.get("jobs", 0)))
        except Exception:
            pass
        self.opt_api.set_active(bool(data.get("api", False)))

def run_gui():
    win = PortatoGUI()
    win.show_all()
    Gtk.main()
    return 0
