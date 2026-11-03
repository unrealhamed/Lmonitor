class PhotoImage:
    def __init__(self, im=None, *a, **k): self.im = im
    def width(self): return self.im.width
    def height(self): return self.im.height
    def paste(self, im): self.im = im
    def configure(self, **k): pass
