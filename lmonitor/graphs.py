"""Short history for the Graphs page: temperatures, usage, network and fan speeds of the last
10 minutes, kept with their real time so any sampling interval gives correct graphs."""
import math
from collections import deque


class GraphHistory:
    KEEP = 600.0
    KEYS = ("c_temp", "g_temp", "c_use", "g_use", "r_use", "net_down", "net_up")
    MAX_GAP = 4.5                                # s; a longer hole is real and stays visible

    def __init__(self):
        self.data = deque()                      # (time, {key: value}, {fan name: rpm})

    def add(self, snap, fans=None, now=None):
        now = float(now)
        self.data.append((now, {k: snap.get(k) for k in self.KEYS}, dict(fans or {})))
        while self.data and self.data[0][0] < now - self.KEEP:
            self.data.popleft()

    def latest(self):
        """Time of the newest reading, or None."""
        return self.data[-1][0] if self.data else None

    @staticmethod
    def _bridge(vals, width, max_gap):
        """Readings do not land exactly once per slot, so a slot can be empty by chance.
        Join such short holes with a straight line; a long hole stays None."""
        last = None
        for i, x in enumerate(vals):
            if x is None:
                continue
            if last is not None and i - last > 1 and (i - last) * width <= max_gap:
                for j in range(last + 1, i):
                    vals[j] = vals[last] + (x - vals[last]) * (j - last) / (i - last)
            last = i
        return vals

    def series(self, seconds, points=60, now=None, max_gap=None):
        """Averages of `points` equal time slots, the last one holding `now`. The slots
        sit on fixed clock boundaries, so a finished slot never changes when time moves
        on. -> {key: [...], "fans": {name: [...]}, "end_ms": end of the last slot}"""
        w = seconds / points
        end = math.ceil(now / w) * w
        gap = self.MAX_GAP if max_gap is None else max_gap
        lead = int(gap // w) + 1                 # hidden slots, so a hole at the left edge is joined too
        start = end - seconds - lead * w
        rows = list(self.data)                   # one atomic copy: the worker keeps appending
        slots = [[] for _ in range(points + lead)]
        for t, vals, fans in rows:
            i = int((t - start) // w)
            if 0 <= i < points + lead:
                slots[i].append((vals, fans))

        def avg(xs):
            xs = [x for x in xs if x is not None]
            return sum(xs) / len(xs) if xs else None
        out = {k: self._bridge([avg([v[k] for v, _ in sl]) for sl in slots], w, gap)[lead:] for k in self.KEYS}
        names = sorted({n for _, _, f in rows for n in f})
        out["fans"] = {n: self._bridge([avg([f.get(n) for _, f in sl]) for sl in slots], w, gap)[lead:] for n in names}
        out["end_ms"] = end * 1000.0
        return out
