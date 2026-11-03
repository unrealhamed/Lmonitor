class Font:
    def __init__(self, **k): self.k = k
    def configure(self, **k): self.k.update(k)
    def measure(self, t): return 8 * len(t)
    def metrics(self, *a): return 16
Font.cget = lambda self, n: self.k.get(n)
