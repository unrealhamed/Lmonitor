class MenuItem:
    def __init__(self, text, action, default=False, checked=None): self.text, self.action, self.checked = text, action, checked
class Menu:
    def __init__(self, *items): self.items = items
class Icon:
    def __init__(self, name, image, title, menu=None): self.name, self.image, self.title, self.menu = name, image, title, menu
    def run(self): pass
    def stop(self): pass
