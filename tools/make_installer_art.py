"""Makes the installer's pictures from Lmonitor's own look (run by build_installer_qt.bat):
installer/art/wizard-<w>x<h>.bmp  (the tall picture on the welcome / finish pages)
installer/art/small-<w>x<h>.bmp   (the logo at the top right of the other pages)
One file per Windows display scale, so the pictures stay sharp. Needs PySide6 only."""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QGuiApplication, QImage, QLinearGradient, QPainter,
                           QRadialGradient)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "installer", "art")
BG0, BG1, MINT, TEXT, SUB = "#0E1014", "#15181D", "#2DD4A0", "#ECEFF3", "#A7AFBB"
ICON = "\uE9D9"         # the same icon as in the window's sidebar (Segoe Fluent Icons)
WIZARD = ((164, 314), (192, 386), (246, 459), (273, 556), (328, 604), (355, 700), (410, 797))
SMALL = ((55, 55), (64, 68), (83, 80), (92, 97), (110, 106), (119, 123), (138, 140))


def pick(*names):
    have = set(QFontDatabase.families())
    return next((n for n in names if n in have), names[-1])


def icon_font(px):
    f = QFont(pick("Segoe Fluent Icons", "Segoe MDL2 Assets"))
    f.setPixelSize(int(px))
    return f


def mark(p, cx, cy, size):
    """The logo: a mint rounded square with the graph icon."""
    r = QRectF(cx - size / 2, cy - size / 2, size, size)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(MINT))
    p.drawRoundedRect(r, size * 0.24, size * 0.24)
    p.setPen(QColor("#0B1015"))
    p.setFont(icon_font(size * 0.56))
    p.drawText(r, Qt.AlignCenter, ICON)


def wizard(w, h):
    img = QImage(w, h, QImage.Format_RGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    g = QLinearGradient(0, 0, 0, h)
    g.setColorAt(0, QColor(BG1))
    g.setColorAt(1, QColor(BG0))
    p.fillRect(img.rect(), g)
    glow = QRadialGradient(QPointF(w * 0.5, h * 0.33), w * 0.9)
    c = QColor(MINT)
    c.setAlpha(46)
    glow.setColorAt(0, c)
    c.setAlpha(0)
    glow.setColorAt(1, c)
    p.fillRect(img.rect(), glow)
    k = w / 164.0
    # a calm line chart at the bottom, like the app's graphs
    p.setPen(QColor(MINT))
    pen = p.pen()
    pen.setWidthF(2 * k)
    c = QColor(MINT)
    c.setAlpha(150)
    pen.setColor(c)
    p.setPen(pen)
    pts = [0.62, 0.55, 0.58, 0.47, 0.5, 0.41, 0.44, 0.36, 0.4, 0.33]
    base, amp = h * 0.92, h * 0.16
    path = [QPointF(w * i / (len(pts) - 1), base - amp * (1 - v)) for i, v in enumerate(pts)]
    for a, b in zip(path, path[1:]):
        p.drawLine(a, b)
    mark(p, w / 2, h * 0.30, 56 * k)
    f = QFont(pick("Segoe UI Variable Display", "Segoe UI Variable", "Segoe UI", "Arial"))
    f.setPixelSize(int(22 * k))
    f.setWeight(QFont.DemiBold)
    p.setFont(f)
    p.setPen(QColor(TEXT))
    p.drawText(QRectF(0, h * 0.30 + 40 * k, w, 30 * k), Qt.AlignHCenter | Qt.AlignTop, "Lmonitor")
    f.setPixelSize(int(10.5 * k))
    f.setWeight(QFont.Normal)
    p.setFont(f)
    p.setPen(QColor(SUB))
    p.drawText(QRectF(8 * k, h * 0.30 + 70 * k, w - 16 * k, 40 * k), Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap,
               "Gaming overlay\nand PC monitor")
    p.end()
    return img


def small(w, h, bg="#FFFFFF"):
    img = QImage(w, h, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    s = min(w, h) * 0.86
    mark(p, w / 2, h / 2, s)
    p.end()
    # BMP has no transparency: a white background for the light wizard, the logo stays readable in dark too
    out = QImage(w, h, QImage.Format_RGB32)
    out.fill(QColor(bg))
    q = QPainter(out)
    q.drawImage(0, 0, img)
    q.end()
    return out


def main():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    os.makedirs(OUT, exist_ok=True)
    for w, h in WIZARD:
        wizard(w, h).save(os.path.join(OUT, "wizard-%dx%d.bmp" % (w, h)))
    for w, h in SMALL:
        small(w, h).save(os.path.join(OUT, "small-%dx%d.bmp" % (w, h)))
        small(w, h, BG0).save(os.path.join(OUT, "small-dark-%dx%d.bmp" % (w, h)))   # Windows in dark mode
    print("installer art:", len(WIZARD) + 2 * len(SMALL), "pictures in", OUT)
    return app


if __name__ == "__main__":
    main()
