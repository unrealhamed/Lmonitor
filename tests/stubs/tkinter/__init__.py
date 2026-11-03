"""Tiny tkinter stand-in: records canvas items so they can be rendered with PIL."""
import itertools
from PIL import Image, ImageDraw, ImageFont
AFTERS = []
_ids = itertools.count(1)
FONTS = {}
def _font(spec, scale=1.0):
    fam, size, *st = spec if isinstance(spec, tuple) else (spec, 10)
    bold = "bold" in st or "semibold" in str(fam).lower()
    key = (bold, int(size * 1.34 * scale))
    if key not in FONTS:
        FONTS[key] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if bold else ""), key[1])
    return FONTS[key]

class Event:
    def __init__(self, x=0, y=0, x_root=0, y_root=0): self.x, self.y, self.x_root, self.y_root = x, y, x_root, y_root

class Misc:
    master = None
    def _reg(self, master):
        self.master = master; self.kids = []; self.binds = getattr(self, "binds", {}); self.attrs = {}
        if master is not None and hasattr(master, "kids"): master.kids.append(self)
    def after(self, ms, fn=None, *a):
        i = next(_ids); AFTERS.append((i, ms, fn, a)); return i
    def after_cancel(self, i):
        AFTERS[:] = [t for t in AFTERS if t[0] != i]
    def bind(self, seq, fn=None, add=None):
        self.__dict__.setdefault("binds", {})[seq] = fn
    def emit(self, seq, **kw):
        fn = self.__dict__.get("binds", {}).get(seq)
        if fn: fn(Event(**kw))
    def configure(self, **k): self.__dict__.setdefault("opts", {}).update(k)
    config = configure
    def winfo_screenwidth(self): return 1920
    def winfo_screenheight(self): return 1080
    def winfo_id(self): return 1
    def update_idletasks(self): pass
    def update(self): pass
    def lift(self): pass
    def attributes(self, *a):
        self.__dict__.setdefault("attrs", {})
        if len(a) == 2: self.attrs[a[0]] = a[1]
        return self.attrs.get(a[0]) if a else None
    def geometry(self, *a): pass
    def title(self, *a): pass
    def resizable(self, *a): pass
    def withdraw(self): pass
    def deiconify(self): pass
    def protocol(self, *a): pass
    def overrideredirect(self, *a): pass
    def iconphoto(self, *a): self.icons = a
    def pack(self, *a, **k): pass
    def place(self, *a, **k): pass
    def grid(self, *a, **k): pass
    def mainloop(self): pass
    def winfo_reqwidth(self): return 200
    def winfo_reqheight(self): return 30
    def winfo_width(self): return 200
    def winfo_height(self): return 30
    def winfo_x(self): return 0
    def winfo_y(self): return 0
    def winfo_children(self): return list(self.__dict__.get("kids", []))
    def destroy(self):
        m = self.master
        if m is not None and self in getattr(m, "kids", []): m.kids.remove(self)
    def pack_forget(self): pass
    def grid_forget(self): pass

class Tk(Misc):
    def __init__(self): self._reg(None)
class Toplevel(Misc):
    def __init__(self, master=None, **k): self.opts = dict(k); self._reg(master)
class Frame(Misc):
    def __init__(self, master=None, **k): self.opts = dict(k); self._reg(master)
class Label(Misc):
    def __init__(self, master=None, **k): self.opts = dict(k); self._reg(master)
    def cget(self, k): return self.opts.get(k, "")
    def __setitem__(self, k, v): self.opts[k] = v
    def __getitem__(self, k): return self.opts.get(k, "")

class Canvas(Misc):
    def __init__(self, master=None, width=200, height=100, bg="#000000", **k):
        self.w, self.h, self.bg = width, height, bg
        self.items = {}; self.cbinds = []; self.opts = {}; self._reg(master)
    def configure(self, **k):
        self.opts.update(k)
        if 'bg' in k: self.bg = k['bg']
    config = configure
    def _new(self, kind, coords, kw):
        i = next(_ids); tags = kw.pop("tags", ()); tags = {tags} if isinstance(tags, str) else set(tags)
        kw.setdefault("state", "normal")
        self.items[i] = dict(kind=kind, c=list(coords), o=kw, tags=tags); return i
    def create_image(self, x, y, **k): return self._new("image", (x, y), k)
    def create_text(self, x, y, **k): return self._new("text", (x, y), k)
    def create_rectangle(self, x1, y1, x2, y2, **k): return self._new("rect", (x1, y1, x2, y2), k)
    def create_line(self, *c, **k): return self._new("line", c, k)
    def create_polygon(self, *c, **k): return self._new("poly", c, k)
    def create_oval(self, *c, **k): return self._new("oval", c, k)
    def _sel(self, t):
        if t == "all": return list(self.items)
        if isinstance(t, int): return [t] if t in self.items else []
        return [i for i, it in self.items.items() if t in it["tags"]]
    def delete(self, t): [self.items.pop(i) for i in self._sel(t)]
    def itemconfig(self, t, **kw):
        for i in self._sel(t): self.items[i]["o"].update(kw)
    itemconfigure = itemconfig
    def itemcget(self, t, k): return self.items[self._sel(t)[0]]["o"].get(k, "")
    def coords(self, t, *c):
        for i in self._sel(t): self.items[i]["c"] = list(c)
    def move(self, t, dx, dy):
        for i in self._sel(t):
            c = self.items[i]["c"]; self.items[i]["c"] = [v + (dx if n % 2 == 0 else dy) for n, v in enumerate(c)]
    def find_all(self): return list(self.items)
    def tag_bind(self, t, seq, fn, add=None):
        if add != "+":
            if any(b[0] == t and b[1] == seq for b in self.cbinds):
                self.replaced = getattr(self, "replaced", []) + [(t, seq)]
            self.cbinds[:] = [b for b in self.cbinds if not (b[0] == t and b[1] == seq)]
        self.cbinds.append((t, seq, fn))
    def tag_lower(self, *a): pass
    def tag_raise(self, *a): pass
    def create_window(self, *a, **k): return 0
    # ---- geometry / rendering helpers
    def _size(self, it):
        o = it["o"]
        if it["kind"] == "image":
            im = o["image"].im; return im.width, im.height
        if it["kind"] == "text":
            f = _font(o.get("font", ("Segoe UI", 10))); b = f.getbbox(str(o.get("text", "")) or " ")
            return b[2] - b[0], b[3] - b[1] + 4
        return 0, 0
    def bbox_of(self, it):
        c = it["c"]
        if it["kind"] == "rect": return tuple(c)
        w, h = self._size(it); x, y = c[0], c[1]; a = it["o"].get("anchor", "center")
        a = {"center": ""}.get(a, a)
        x0 = x - w if a.endswith("e") else (x if a.endswith("w") else x - w / 2)
        y0 = y if a.startswith("n") else (y - h if a.startswith("s") else y - h / 2)
        return x0, y0, x0 + w, y0 + h
    def hit(self, x, y, seq="<Button-1>"):
        for i in sorted(self.items, reverse=True):
            it = self.items[i]
            if it["o"].get("state") == "hidden": continue
            if it["kind"] == "rect" and not it["o"].get("fill"): continue
            x0, y0, x1, y1 = self.bbox_of(it)
            if x0 <= x <= x1 and y0 <= y <= y1:
                for t, s, fn in self.cbinds:
                    if s == seq and t in it["tags"]: return fn
                if it["kind"] != "text" or True:
                    # opaque item without a handler blocks items below it only if it has fill/image
                    if it["kind"] in ("rect", "image"): pass
        return None
    def click(self, x, y, seq="<Button-1>"):
        """Fire every handler bound to the items under the point (topmost first)."""
        fired = 0
        for i in sorted(self.items, reverse=True):
            it = self.items[i]
            if it["o"].get("state") == "hidden": continue
            if it["kind"] == "rect" and not it["o"].get("fill"): continue
            x0, y0, x1, y1 = self.bbox_of(it)
            if it["kind"] == "text" and not str(it["o"].get("text", "")): continue
            if it["kind"] == "image" and (x1 - x0) <= 2: continue
            if x0 <= x <= x1 and y0 <= y <= y1:
                # like Tk: only the TOPMOST item under the mouse gets the click
                hs = [fn for t, s, fn in self.cbinds if s == seq and t in it["tags"]]
                for fn in hs: fn(Event(x, y))
                return bool(hs)
        return False
    def config_(self): pass
    def emit_tag(self, tag, seq, x=0, y=0):
        for t, sq, fn in self.cbinds:
            if t == tag and sq == seq: fn(Event(x, y))
    def render(self, path, scale=1):
        img = Image.new("RGBA", (self.w, self.h), self.bg)
        d = ImageDraw.Draw(img)
        for i in sorted(self.items):
            it = self.items[i]; o = it["o"]
            if o.get("state") == "hidden": continue
            if it["kind"] == "image" and "image" in o:
                x0, y0, _, _ = self.bbox_of(it); im = o["image"].im.convert("RGBA")
                img.paste(im, (int(round(x0)), int(round(y0))), im)
            elif it["kind"] == "rect" and o.get("fill"):
                d.rectangle(it["c"], fill=o["fill"])
            elif it["kind"] == "line" and o.get("fill") and len(it["c"]) >= 4 and any(it["c"]):
                d.line(it["c"], fill=o["fill"], width=int(o.get("width", 1)))
            elif it["kind"] == "poly" and o.get("fill") and len(it["c"]) >= 6 and any(it["c"]):
                d.polygon(it["c"], fill=o["fill"])
            elif it["kind"] == "oval" and o.get("fill") and any(it["c"]):
                d.ellipse(it["c"], fill=o["fill"])
            elif it["kind"] == "text":
                x0, y0, x1, y1 = self.bbox_of(it)
                d.text((x0, y0 - 1), str(o.get("text", "")), font=_font(o.get("font", ("Segoe UI", 10))), fill=o.get("fill", "#000000"))
        if scale != 1: img = img.resize((self.w * scale, self.h * scale), Image.LANCZOS)
        __import__("os").makedirs(__import__("os").path.dirname(path), exist_ok=True)
        img.convert("RGB").save(path); return path

class Entry(Misc):
    def __init__(self, *a, **k): self._t = ""
    def get(self): return self._t
    def insert(self, i, t): self._t = t
    def delete(self, a, b=None): self._t = ""
