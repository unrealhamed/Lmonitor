"""Headless Lmonitor backend: the engine without any window.

A UI (Qt today) creates one Backend, calls ``sample()`` from a worker thread
and reads plain dictionaries from ``dashboard()``. Nothing here imports a UI
toolkit, and nothing here blocks on the UI thread's behalf.
"""
import getpass
import math
import platform
import time
import psutil
from copy import deepcopy

from lmonitor.graphs import GraphHistory
from lmonitor.engine import (AppInfo, CardStatus, ChangeLog, CpuLoad, Hud, SafeMode, Optimizer, Reports, SessionRecorder,
                             SessionStore, SessionView, Storage, fmt_size, pretty_name, Metrics, OverlayModel, CpuReader, DiagAnalyzer,
                             DiagRunner, FpsMonitor, GpuReader, LibreHardwareHost,
                             Logger, MemoryReader, Recorder, ReportBuilder,
                             ScanStore, SessionAnalyzer, Settings, Telemetry,
                             Theme, WinApi, GameSettings, fmt_net, Profiles)

HW_TABS = (("CPU / GPU", "rows_processor"), ("Memory", "rows_memory"),
           ("Storage", "rows_storage"), ("Network", "rows_network"),
           ("Sensors", "rows_sensors"), ("System", "rows_system"))
HIST = 62            # samples for a sparkline: 60 shown + the ones sliding in and out
RANGES = (("Real time", 0), ("1 min", 60))     # time spans of every chart in the window


class Backend:
    def __init__(self):
        self.settings = Settings()
        self.host = LibreHardwareHost()
        self.cpu = CpuReader(self.host)
        self.gpu = GpuReader(self.host)
        Theme.apply_vendor(self.gpu.vendor())
        Theme.apply_ui(self.settings["ui_theme"], self.settings["ui_accent"])
        self.memory = MemoryReader()
        self.fps = FpsMonitor()
        self.recorder = Recorder(self.gpu)
        self.graphs = GraphHistory()
        self.graph_fans = False         # fan RPM is read only while the Graphs page is open
        self.scanner = DiagRunner(ScanStore())
        self.telemetry = Telemetry(self.host, self.cpu, self.gpu, self.memory)
        self.telemetry.set_interval(self.settings["refresh"])
        self.telemetry.is_admin = lambda: WinApi.admin
        self.telemetry.driver_ok = lambda: True   # the UI may replace this
        self.overlay_model = OverlayModel(self.settings, self.cpu, self.gpu,
                                          self.memory, self.fps)
        self.session_store = SessionStore()
        self.session_store.clear_live()
        self.change_log = ChangeLog()
        self.optimizer = Optimizer(self.change_log)
        self.storage = Storage(self.change_log)
        self.reports = Reports(self.scanner.store, self.session_store, self.change_log)
        self.sessions = SessionRecorder(self.fps, self.cpu, self.gpu, self.session_store,
                                        lambda: self.settings["sessions_on"])
        self._sys_cache, self._sys_t, self._fps_try = {}, 0.0, 0.0
        # graph overlay: its own short history (5 min at most, 4 readings/s in real time)
        self.hud_hist = GraphHistory(keys=self.HUD_KEYS, keep=330)
        self._hud_t, self._hud_live = 0.0, {}
        self._hud_load = CpuLoad()                  # its own CPU counters

    # ---- anti-cheat safe mode (see engine.SafeMode)
    safe_active, safe_game, _safe_t = False, "", 0.0

    def safe_tick(self, now=None):
        """Every 5 s: is a protected game running? Then stop using the sensor driver."""
        now = time.monotonic() if now is None else now
        if now - self._safe_t < 5.0 and self._safe_t:
            return self.safe_active
        self._safe_t = now
        mode = self.settings["safe_mode"]
        game = SafeMode.running() if mode == "auto" else ""
        active = mode == "always" or bool(game)
        self.safe_game = game
        if active != self.safe_active:
            self.safe_active = active
            self.sessions.safe = active
            if active:
                self.host.suspend()
            else:
                self.host.resume()
        return active

    # ---- worker-thread side
    def sample(self):
        """One telemetry reading (call from a worker thread, never the UI)."""
        self.telemetry.sample()
        self.recorder.tick(self.telemetry.snap)     # reuses this reading
        fans = ({n: v for _, _, st, n, v in self.telemetry.sensors.read() if st == "Fan"}
                if self.graph_fans else None)
        self.graphs.add(self.telemetry.snap, fans, time.time())

    def graph_series(self, seconds):
        """Lines for the charts of the window. seconds = 0: real time (the last 10 s, from
        the 4-a-second readings); else that many seconds in 60 slots.
        Some slots are kept outside the chart, so a new point is already drawn before it
        scrolls into view. Anchored on the newest reading, so the last slot holds a value."""
        if not seconds:
            n, span, period, hist = 40, Hud.REALTIME_SECONDS, Hud.REALTIME_PERIOD, self.hud_hist
            gap = max(4 * period, 1.5)
        else:
            n, span, period, hist = 60, seconds, self.telemetry.interval, self.graphs
            gap = max(GraphHistory.MAX_GAP, self.telemetry.interval * 2.2)
        width = span / n
        late = period * 1.2                          # how long a reading may take to arrive
        extra = math.ceil(late / width) + 3
        latest = hist.latest() or time.time()
        s = hist.series(width * (n + extra), n + extra, latest, gap)
        if hist is not self.graphs:                  # fan speeds are read once a second
            s["fans"] = self.graphs.series(width * (n + extra), n + extra, latest,
                                           max(GraphHistory.MAX_GAP, self.telemetry.interval * 2.2))["fans"]
        s["extra"], s["delay_ms"] = extra, (width + late) * 1000.0
        s["points"], s["slot_ms"] = n, width * 1000.0
        return s

    # ---- read side (cheap, no hardware access)
    def version(self):
        return AppInfo.VERSION

    def dashboard(self, range_index=0):
        """Everything the dashboard shows, as plain data. Missing values are
        None and the matching status is "none" - never a made-up number."""
        tel = self.telemetry
        s = tel.snap
        if not s:
            return {"ready": False}
        h = tel.history

        def last(key):
            return [v for v in list(h[key])[-HIST:]]
        t, gt, vm = s["c_temp"], s["g_temp"], s["vm"]
        c = s["c_clk"]
        gclk = s["g_clk"]
        cards = {
            "cpu": {"use": s["c_use"], "temp": t,
                    "status": CardStatus.heat(s["c_use"], t, SessionAnalyzer.CPU_HOT),
                    "clock_mhz": c, "approx": bool(s["c_approx"]),
                    "power_w": s["c_pow"], "hist": last("c_use")},
            "gpu": {"use": s["g_use"], "temp": gt,
                    "status": CardStatus.heat(s["g_use"], gt, SessionAnalyzer.GPU_HOT),
                    "clock_mhz": gclk, "power_w": s["g_pow"], "hist": last("g_use")},
            "ram": {"use": s["r_use"], "used_gb": vm.used / 1024 ** 3,
                    "total_gb": vm.total / 1024 ** 3,
                    "status": CardStatus.ram(s["r_use"]), "hist": last("r_use")},
        }
        rows = tel.storage._rows
        if rows:
            d = rows[0]
            free_pct = 100 - d["pct"]
            cards["disk"] = {"use": d["pct"], "free_gb": d["free"] / 1024 ** 3,
                             "mount": d["mount"].rstrip("\\"),
                             "status": CardStatus.disk(free_pct)}
        else:
            cards["disk"] = {"use": None, "status": "none"}
        cards["cpu"]["note"] = self._cpu_note(t)
        cards["cpu"]["name"] = self._cpu_name()
        cards["gpu"]["name"] = self._gpu_name()
        sc = ReportBuilder.score(self.scanner.issues)
        fps = self.fps
        return {
            "ready": True, "cards": cards, "pc": platform.node(), "user": self._user(),
            "network": {"down": fmt_net(s["net_down"], self.settings["net_unit"]),
                        "up": fmt_net(s["net_up"], self.settings["net_unit"]),
                        "hist": [v for v in list(h["net_down"])[-HIST:]]},
            "status": {"score": sc["value"], "covered": sc["covered"],
                       "total": sc["total"],
                       "cpu_sensor": t is not None, "gpu_sensor": gt is not None,
                       "fps": "ready" if fps.alive else (
                           "missing" if "not found" in (fps.status or "") else "idle")},
            "safe": {"active": self.safe_active, "game": self.safe_game},
            "now": self.now_box(),
        }

    _last_sess, _last_sess_t = None, 0.0

    def now_box(self):
        """What is going on right now, for the Home page: the game in front and its frame
        rate, the session recorder, the last saved session. Real values or None."""
        game = None
        try:
            if self.fps.alive:
                cur, snap = self.fps.current(), self.fps.snapshot(False)
                if cur and snap:
                    game = {"name": cur[1], "fps": round(snap[0]), "avg": round(snap[1]),
                            "low": round(snap[2]) if snap[2] else None}
        except Exception:
            Logger.error("now box fps")
        text, rec = "", False
        try:
            text, rec = self.sessions.status()
        except Exception:
            Logger.error("now box session")
        now = time.monotonic()
        if now - self._last_sess_t > 15 or not self._last_sess_t:      # the database: not every second
            self._last_sess_t = now
            self._last_sess = None
            try:
                for it in self.session_store.list():
                    if not it["summary"].get("live"):
                        self._last_sess = {"game": it["game"], "when": self._when(it["start"]),
                                           "avg_fps": it["summary"].get("avg_fps")}
                        break
            except Exception:
                Logger.error("now box last session")
        return {"game": game, "session": text, "recording": bool(rec), "last": self._last_sess}

    def _cpu_note(self, temp):
        """Why the CPU temperature is missing (real reason), else ""."""
        if temp is not None:
            return ""
        if self.safe_active:
            return "Paused by anti-cheat safe mode"
        if not WinApi.is_admin():
            return "Run as administrator for CPU temperature"
        hint = self.telemetry._cpu_hint(None) or ""
        return hint.replace("n/a", "").strip(" ()") or "CPU sensor not available"

    def interval_ms(self):
        return int(self.telemetry.interval * 1000)

    def _cpu_name(self):
        try:
            return (self.host.cpu_name_raw or self.telemetry.info.cpu_registry or "").strip()
        except Exception:
            return ""

    def _gpu_name(self):
        try:
            n = self.gpu.display_name()
            return pretty_name(n) if n else ""
        except Exception:
            return ""

    @staticmethod
    def _user():
        try:
            return getpass.getuser()
        except Exception:
            return ""

    def hardware_sections(self, tab):
        """Hardware rows grouped into sections [{title, rows}], and split in
        two columns of similar height for the page."""
        secs = []
        for r in self.hardware(tab):
            if r[0] == "head":
                secs.append({"title": str(r[1]), "rows": []})
                continue
            if not secs:
                secs.append({"title": "", "rows": []})
            secs[-1]["rows"].append({"kind": r[0], "a": str(r[1]),
                                     "b": str(r[2]) if len(r) > 2 else "",
                                     "c": r[3] if len(r) > 3 else None})
        cols, heights = [[], []], [0, 0]
        for sec in secs:
            i = 0 if heights[0] <= heights[1] else 1
            cols[i].append(sec)
            heights[i] += len(sec["rows"]) + 2
        return cols

    # ---- hardware page
    def hardware(self, tab):
        """Rows of one Hardware tab: ("head", t) / ("row", k, v[, color]) /
        ("bar", k, v, fraction). Reads cached telemetry only."""
        rows = getattr(self.telemetry, HW_TABS[tab][1])()
        return [list(r) for r in rows]

    # ---- settings (validated by the engine, saved by the caller)
    def settings_view(self):
        d = deepcopy(self.settings.data)
        d["value_hex"] = self.value_hex()
        d["group_colors"] = self.group_colors()
        return d

    def set_setting(self, key, value):
        """Set one setting through the engine's validation. -> True if known."""
        if key not in Settings.DEFAULTS:
            return False
        cfg = deepcopy(self.settings.data)
        cfg[key] = value
        self.settings.data.update(Settings._clean(cfg))
        self.overlay_changed()
        return True

    def set_many(self, values):
        """Several settings that only make sense together (a saved place = monitor + x +
        y + "custom"): all are put in first, then checked once. One at a time the check
        would throw away an x that has no y yet."""
        if any(k not in Settings.DEFAULTS for k in values):
            return False
        cfg = deepcopy(self.settings.data)
        cfg.update(values)
        self.settings.data.update(Settings._clean(cfg))
        self.overlay_changed()
        return True

    def set_show(self, key, on):
        if key not in Metrics.KEYS:
            return False
        self.settings.data["show"][key] = bool(on)
        self.overlay_changed()
        return True

    def set_density(self, key):
        show = Profiles.density_show(key)
        if show is None:
            return False
        self.settings.data["show"] = show
        self.overlay_changed()
        return True

    def density(self):
        return Profiles.density_of(self.settings.show)

    QT_DEFAULT = {"bg0": "#08080a", "bg1": "#0e0e11", "card": "#131316",
                  "cardHi": "#1a1a1f", "line": "#26262c", "text": "#f4f4f6",
                  "sub": "#a0a0aa", "dim": "#64646e", "accent": "#1fd18b",
                  "light": False}

    def ui_style(self, theme=None, accent=None):
        """Colors of the window for a theme + accent (plain data, no UI)."""
        theme = theme or self.settings["ui_theme"]
        accent = accent or self.settings["ui_accent"]
        spec = Theme.ui_spec(theme)
        if theme == "default":
            d = dict(self.QT_DEFAULT)
            base = d["accent"]
        else:
            light = spec["light"]
            d = {"bg0": spec["C_BG"], "bg1": spec["C_SIDE"], "card": spec["C_CARD"],
                 "cardHi": Theme.mix(spec["C_CARD"], "#000000" if light else "#ffffff", 0.05),
                 "line": spec["C_TRACK"], "text": spec["TXT"], "sub": spec["SUB"],
                 "dim": spec["DIM"], "light": light}
            base = spec["accent"] or Theme.VENDOR["accent"]
        chosen = dict((k, c) for k, _, c in Theme.UI_ACCENTS).get(accent)
        if accent == "custom":
            chosen = Theme.hue_hex(self.settings["ui_hue"])
        if chosen:
            base = chosen
        if d["light"]:
            base = Theme.mix(base, "#000000", 0.16)
        d["accent"] = base
        d["accentText"] = Theme._on_color(base)
        d["radius"] = dict(Theme.UI_RADII)[self.settings["ui_radius"]]
        d["font"] = self.settings["ui_font"]
        d["zoom"] = self.settings["ui_scale"] / 100.0
        return d

    def set_order(self, order):
        self.settings.data["order"] = Metrics.clean_order(order)

    def reset_settings(self):
        self.settings.reset()

    def save_settings(self):
        self.settings.save()

    def value_hex(self):
        for k, _, col in Theme.VALUE_COLORS:
            if k == self.settings["value_color"]:
                return col or Theme.ACCENT
        return Theme.WHITE

    def group_colors(self):
        cols = {"FPS": Theme.WHITE, "GPU": self.gpu.brand_color(),
                "CPU": self.cpu.brand_color(), "RAM": Theme.GRAY,
                "NET": Theme.NET_COLOR}
        cols.update(Theme.palette(self.settings["palette"]) or {})
        return cols

    # ---- overlay
    def overlay_read(self):
        """One reading of the bar's items (worker thread). -> {key: (text, color)}.
        The sensors are read at most once per Refresh interval; the FPS items
        (cheap, from memory) are refreshed on every call."""
        need = self.overlay_model.need()
        now = time.monotonic()
        if now - self._sys_t >= max(0.5, float(self.settings["refresh"])) - 0.05 or not self._sys_cache:
            self._sys_cache = self.overlay_model.system(need)
            self._sys_t = now
        out = dict(self._sys_cache)
        if need.get("FPS"):
            items, graph = self.overlay_model.frames(self.settings.show.get("graph", False))
            out.update(items)
            out["__graph"] = graph
        return out

    def overlay_changed(self):
        """Settings changed: read the sensors again on the next round."""
        self._sys_t = 0.0

    def ensure_fps(self, overlay_wants_fps):
        """PresentMon runs only while something needs it (FPS in the bar, or
        session recording). Retried at most every 10 seconds."""
        want = bool(overlay_wants_fps or self.settings["sessions_on"])
        if want and not self.fps.alive:
            now = time.monotonic()
            if now - self._fps_try >= 10:
                self._fps_try = now
                self.fps.start()
        elif not want and self.fps.alive:
            self.fps.stop()

    def overlay_view(self, texts):
        """Compose what the bar draws: groups in the user's order, only the
        items that are switched on. Plain data (no colors resolved by the UI)."""
        show, vh, gc = self.settings.show, self.value_hex(), self.group_colors()
        groups = []
        for gname, items in Metrics.ordered(self.settings["order"]):
            vis = [it for it in items if show.get(it[0])]
            if not vis:
                continue
            rows = []
            for key, label, _w in vis:
                if key == "graph":
                    continue
                text, color = texts.get(key, ("--", None))
                rows.append({"key": key, "label": label, "text": text,
                             "color": color if color and color != Theme.WHITE else vh})
            groups.append({"name": gname, "color": gc.get(gname, Theme.WHITE),
                           "items": rows,
                           "graph": any(it[0] == "graph" for it in vis)})
        return {"groups": groups, "graph": texts.get("__graph")}

    # ================================================= graph overlay (HUD)
    HUD_POINTS = 60                       # points per chart (the frame-time chart: 2x)
    HUD_FLOOR = {"fps": 60, "ft": 20, "g_pow": 40, "c_pow": 30}   # smallest scale top

    HUD_KEYS = ("fps", "ft", "g_temp", "c_temp", "g_use", "c_use", "r_use", "g_pow", "c_pow",
                "net_down", "net_up")
    HUD_FAST = {"g_use": True, "g_temp": True, "g_pow": True, "g_clk": False, "g_mem": False}

    hud_page_open = False               # the settings page shows a live preview

    def _hud_active(self):
        """Prefixes of the graph overlays that are switched on (all while the page is open)."""
        S = self.settings
        return [p for p in Settings.HUD_PREFIXES if S[p + "on"] or self.hud_page_open]

    def hud_wants_fps(self):
        return any(k in ("fps", "ft") for p in self._hud_active() for k in self.settings[p + "items"])

    graph_fast = False                  # a page of the window shows real-time charts

    def hud_realtime(self):
        """Are fast readings (4 a second) needed now?"""
        return self.graph_fast or any(self.settings[p + "window"] == 0 for p in self._hud_active())

    def hud_period(self):
        """Seconds between two graph-overlay readings."""
        return Hud.REALTIME_PERIOD if self.hud_realtime() else 1.0

    def hud_tick(self, now=None):
        """One graph-overlay reading when it is due (worker thread). Normal spans reuse the
        dashboard's reading of each second; real time reads 4x a second, but only cheap
        sources: NVML (NVIDIA), Windows CPU / RAM counters and PresentMon's frame list.
        CPU temperature / power stay at the once-a-second sensor reading. -> True if read."""
        now = time.time() if now is None else now
        period = self.hud_period()
        if now - self._hud_t < period * 0.85:
            return False
        since, self._hud_t = self._hud_t or now - period, now
        live = self.telemetry.snap or {}
        vals = {k: live.get(k) for k in ("g_temp", "c_temp", "g_use", "c_use", "r_use", "g_pow", "c_pow",
                                          "net_down", "net_up")}
        if self.hud_realtime():
            try:
                use, temp, pw, _clk, _mem = self.gpu.read(self.HUD_FAST, nvml_only=True)
                if self.gpu.available:
                    vals.update(g_use=use, g_temp=temp, g_pow=pw)
                vals["c_use"] = self._hud_load.read()
                vals["r_use"] = psutil.virtual_memory().percent
            except Exception:
                Logger.error("hud fast read")
        st = self.fps.recent_stats(since) if self.fps.alive else None
        vals["fps"], vals["ft"] = (st if st else (None, None))
        self.hud_hist.add(vals, None, now)
        self._hud_live = vals
        return True

    @staticmethod
    def _nice_max(vals, floor):
        """Top of a scale: a round number a little above the data (never below `floor`)."""
        m = max([v for v in vals if v is not None] or [0]) * 1.08
        m = max(float(floor), m)
        p = 10 ** math.floor(math.log10(m))
        for f in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
            if m <= f * p + 1e-9:
                return f * p
        return 10 * p

    @staticmethod
    def _hud_text(key, v):
        if v is None:
            return "--"
        if key == "ft":
            return f"{v:.1f}"
        return f"{v:.0f}"

    def hud_views(self):
        """One view per graph overlay (1 and 2)."""
        return [self.hud_view(p) for p in Settings.HUD_PREFIXES]

    def hud_view(self, prefix="hud_"):
        """What a graph overlay draws: one entry per chosen chart. Plain data; a missing
        sensor gives "--" and an empty line (never a made-up number).

        The charts sit on fixed time slots (like the Graphs page): `extra` slots are kept
        outside the plot so a new point is already drawn before it scrolls into view;
        end_ms / slot_ms / delay_ms let the overlay scroll smoothly between readings.
        lo / hi are the real lowest / highest readings of the span (not slot averages)."""
        S = self.settings
        realtime = S[prefix + "window"] == 0
        sec = Hud.REALTIME_SECONDS if realtime else S[prefix + "window"]
        n = 40 if realtime else self.HUD_POINTS
        w = sec / n
        period = self.hud_period()            # readings come at the fastest overlay's pace
        late = period * 1.5                                  # a reading may come this late
        extra = math.ceil(late / w) + 2
        now = time.time()
        latest = self.hud_hist.latest() or now
        gap = max(4 * period, 1.0) if realtime else GraphHistory.MAX_GAP
        s = self.hud_hist.series(w * (n + extra), n + extra, latest, gap)
        raw = self.hud_hist.raw(latest - sec)
        accent, colors = Hud.theme(S[prefix + "theme"])
        live = self._hud_live or {}
        items = []
        for i, key in enumerate(S[prefix + "items"]):
            title, unit, fixed = Hud.ITEMS[key]
            series = list(s.get(key) or [None] * (n + extra))
            seen = [v[key] for _, v in raw if v.get(key) is not None]
            items.append({"key": key, "title": title, "unit": unit,
                          "text": self._hud_text(key, live.get(key)),
                          "series": series,
                          "max": fixed or self._nice_max(seen, self.HUD_FLOOR.get(key, 10)),
                          "lo": self._hud_text(key, min(seen)) if seen else "--",
                          "hi": self._hud_text(key, max(seen)) if seen else "--",
                          "color": colors[i % len(colors)]})
        return {"items": items, "accent": accent, "window": sec, "realtime": realtime,
                "points": n, "extra": extra, "end_ms": s["end_ms"], "slot_ms": w * 1000.0,
                "delay_ms": (w + late) * 1000.0}

    # ================================================= tools pages (plain data)
    @staticmethod
    def _when(t):
        return time.strftime("%d %b %Y  %H:%M", time.localtime(t)) if t else ""

    @staticmethod
    def sections(rows):
        """("head", t) / ("row", k, v[, color]) / ("bar", ...) rows -> [{title, rows}]"""
        secs = []
        for r in rows:
            if r[0] == "head":
                secs.append({"title": str(r[1]), "rows": []})
                continue
            if not secs:
                secs.append({"title": "", "rows": []})
            secs[-1]["rows"].append({"kind": r[0], "a": str(r[1]),
                                     "b": str(r[2]) if len(r) > 2 else "",
                                     "c": r[3] if len(r) > 3 else None})
        return secs

    OPEN_TEXT = {"ms-settings:startupapps": "Open Startup Apps",
                 "control powercfg.cpl": "Open Power Options",
                 "ms-settings:storagesense": "Open Storage Sense",
                 "devmgmt.msc": "Open Device Manager",
                 "eventvwr.msc": "Open Event Viewer",
                 "services.msc": "Open Services",
                 "ms-settings:gaming-gamemode": "Open Game Mode",
                 "SystemPropertiesPerformance.exe": "Open Performance options"}
    # issues Lmonitor itself can act on: area -> page that does it
    GOTO = {"Startup": "Optimizer", "Power": "Optimizer", "Settings": "Optimizer",
            "Disks": "Storage"}

    def tools_diag(self):
        r = self.scanner
        issues = [{"id": i["id"], "area": i["area"], "title": i["title"], "sev": i["sev"],
                   "word": DiagAnalyzer.SEV_WORD.get(i["sev"], ""),
                   "evidence": [str(e) for e in i["evidence"]],
                   "explain": i["explain"], "fix": i["fix"],
                   "open": i.get("open") or "",
                   "open_text": self.OPEN_TEXT.get(i.get("open") or "", ""),
                   "goto": self.GOTO.get(i["area"], "") if i["sev"] in ("warn", "notice", "info") else ""}
                  for i in r.issues]
        return {"running": r.running, "progress": r.progress, "has": bool(r.when),
                "when": self._when(r.when), "summary": r.summary or {}, "issues": issues}

    def tools_opt(self):
        o = self.optimizer
        startup = [{"key": i["key"], "name": i["name"], "where": i["where"],
                    "cmd": i["cmd"], "enabled": bool(i["enabled"])} for i in o.startup]
        plans = [dict(p) for p in o.plans] if o.plans else []
        settings = []
        for sid, it in GameSettings.ITEMS.items():
            st = o.settings.get(sid)
            if st:
                settings.append({"sid": sid, "title": it["title"], "sub": it["sub"],
                                 "good": bool(st[1]), "text": st[2], "button": it["button"]})
        presets = []
        for name, title in (("gaming", "Gaming"), ("balanced", "Balanced")):
            presets.append({"name": name, "title": title,
                            "steps": [x[0] for x in o.preset_steps(name)],
                            "note": o.preset_note(name)})
        hist = []
        for c in reversed(self.change_log.load()[-30:]):
            hist.append({"id": c["id"], "when": self._when(c["t"]), "title": c["title"],
                         "before": c.get("before", ""), "after": c.get("after", ""),
                         "status": c.get("status", ""),
                         "undo": bool(c.get("revert")) and c.get("status") == "applied"})
        return {"busy": o.busy, "refreshed": o.refreshed, "startup": startup,
                "plans": plans, "plans_ok": o.plans is not None, "settings": settings,
                "presets": presets, "history": hist, "last": o.last}

    def tools_storage(self):
        st = self.storage
        caches = []
        for lid, title, path, note in st.cache_locations():
            r = st.caches.get(lid)
            caches.append({"id": lid, "title": title, "note": note,
                           "recommended": lid in st.RECOMMENDED,
                           "scanned": lid in st.caches, "present": bool(path) and r is not None,
                           "old": fmt_size(r["old_bytes"]) if r else "",
                           "old_bytes": r["old_bytes"] if r else 0,
                           "files": r["old_files"] if r else 0,
                           "all": fmt_size(r["bytes"]) if r else ""})
        drives = [{"mount": d["mount"].rstrip("\\"), "label": d["label"], "pct": d["pct"],
                   "free": fmt_size(d["free"]), "total": fmt_size(d["total"])}
                  for d in self.telemetry.storage.read()]
        fol = [{"path": f["path"], "size": fmt_size(f["bytes"]), "files": f["files"],
                "partial": f["partial"], "reason": f["reason"] or ""} for f in (st.folders or [])]
        big = [{"path": f["path"], "size": fmt_size(f["bytes"]), "reason": f["reason"] or "",
                "deletable": bool(f["deletable"])} for f in (st.large or [])]
        return {"busy": st.busy, "progress": st.progress, "scanned": st.scanned,
                "reclaimable": fmt_size(st.reclaimable()), "caches": caches, "drives": drives,
                "folders": fol, "large": big, "folders_done": st.folders is not None,
                "large_done": st.large is not None, "last": st.last}

    def tools_reports(self):
        rp = self.reports
        rep = rp.report
        out = {"busy": rp.busy, "last": rp.last, "folder": rp.folder(), "built": rep is not None}
        if rep:
            sc = rep["score"]
            out.update({"score": sc["value"], "covered": sc["covered"], "total": sc["total"],
                        "generated": self._when(rep["generated"]),
                        "scan_time": self._when(rep["scan_time"]), "issues": len(rep["issues"]),
                        "ok_count": rep["ok_count"], "sessions": len(rep["sessions"]),
                        "changes": len(rep["changes"])})
        return out

    def tools_sessions(self):
        status, rec = self.sessions.status()
        items = []
        for s in self.session_store.list():
            sm = s["summary"]
            items.append({"id": s["id"], "game": s["game"], "when": self._when(s["start"]),
                          "duration": SessionView.clock(s["duration"]),
                          "avg_fps": sm.get("avg_fps"), "low1": sm.get("low1"),
                          "live": bool(sm.get("live"))})
        return {"status": status, "recording": rec, "enabled": bool(self.settings["sessions_on"]),
                "items": items}

    def session_detail(self, sid):
        """Sections of one session: summary, findings, drops, apps."""
        sm = next((x["summary"] for x in self.session_store.list() if x["id"] == sid), None)
        if sm is None:
            return []
        rows = (SessionView.rows_summary(sm) + [("head", "What was found")]
                + SessionView.rows_findings(sm) + SessionView.rows_drops(sm)
                + SessionView.rows_apps(sm))
        return self.sections(rows)

    def close(self):
        """Stop what the engine started (sensor host, PresentMon)."""
        try:
            self.fps.stop()
        except Exception:
            Logger.error("backend close")
