"""v1.17.4 - full Persian: right-to-left window, translated engine texts, mixed text order."""
import os as _os, sys, re, json
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

QML = _os.path.join(ROOT, "lmonitor", "qt", "qml")
def read(*p): return open(_os.path.join(QML, *p), encoding="utf-8").read()

# ---- structure
main = read("Main.qml")
chk("the whole window is mirrored in Persian", "xScale: Tr.rtl ? -1 : 1" in main and "id: stage" in main)
txt = read("components", "Text.qml")
chk("one Text for every page, it turns itself back", "Q.Text {" in txt and "Tr.mirrored(t.parent)" in txt)
chk("left / right alignment swapped in Persian", "AlignLeft) t.horizontalAlignment = Q.Text.AlignRight" in txt)
chk("a text being deleted is skipped (no errors)", 'typeof t.lmApply === "function"' in txt)
comp_dir = _os.path.join(QML, "components")
missing = []
for f in sorted(_os.listdir(comp_dir)):
    if f.endswith(".qml") and f != "Text.qml":
        s = open(_os.path.join(comp_dir, f), encoding="utf-8").read()
        if re.search(r"\bText\s*\{", s) and 'import "."' not in s:
            missing.append(f)
chk("every component uses the upright Text (import \".\")", not missing)
for f in ("GraphChart.qml", "LiveCanvas.qml", "GraphHud.qml", "OverlayBar.qml"):
    chk("%s keeps left-to-right inside the mirrored window" % f, "function checkUpright" in read("components", f))
chk("the graph-overlay preview is a picture of the screen (not mirrored)",
    "function checkUpright" in read("pages", "HudPage.qml"))
tr = read("Lmonitor", "Tr.qml")
chk("texts with numbers are matched by patterns", "Fa.patterns" in tr)
chk("long texts are translated sentence by sentence", "\\u0001" in tr)
chk("English / number groups kept in one piece (isolates)", "\\u2066" in tr and "\\u2069" in tr)

# ---- every Tr.t("...") key of the pages has Persian (units / codes excepted)
fa = read("Lmonitor", "fa.js")
keys = set(re.findall(r'"((?:[^"\\]|\\.)*)"\s*:', fa))
ok_without = {"GHz", "RPM", " RPM", " GHz", " GB", " MB", " KB", "GB", "MB", "KB", "CPU ", "GPU ", "English"}
miss = []
for dp, _, fs in _os.walk(QML):
    for f in fs:
        if f.endswith(".qml"):
            s = open(_os.path.join(dp, f), encoding="utf-8").read()
            for k in re.findall(r'Tr\.t\("((?:[^"\\]|\\.)*)"\)', s):
                if k not in keys and k not in ok_without and re.search(r"[A-Za-z]{3,}", k):
                    miss.append(k)
chk("every page text has Persian (%d missing: %s)" % (len(miss), miss[:5]), not miss)

# ---- real translation in Qt's JavaScript engine
try:
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlEngine, QQmlComponent
    from PySide6.QtCore import QUrl
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    e = QQmlEngine()
    e.addImportPath(QML)
    samples = ["Game Mode: Not set (Windows default) -> On", "Free space on C:",
               "C:  275 GB free of 476 GB (58 % free)", "n/a", "2300 MHz (Windows value)",
               "Programs that start with Windows use memory and some CPU in the background and slow the start. 9 is above our guideline of 8.",
               "Low RAM: 30 s at 90%+ used (peak 95%, lowest free 0.8 GB)", "Untranslated English stays.", " free of "]
    c = QQmlComponent(e)
    c.setData(("import QtQuick\nimport Lmonitor\nQtObject {\n property var out: { Tr.lang = 'fa'; var s = %s; "
               "var r = s.map(function (x) { return Tr.t(x) }); r.push(Tr.line('275 GB' + Tr.t(' free of ') + '352 GB')); "
               "Tr.lang = 'en'; r.push(Tr.t('Free space on C:')); return r }\n}\n" % json.dumps(samples)).encode(),
              QUrl.fromLocalFile(_os.path.join(QML, "t27.qml")))
    o = c.create()
    out = o.property("out") if o else None
    out = out.toVariant() if hasattr(out, "toVariant") else out
    if not out:
        chk("QML loads: %s" % [x.toString() for x in c.errors()], False)
    else:
        clean = [x.replace("‏", "").replace("⁦", "").replace("⁩", "") for x in out]
        chk("arrow change translated", clean[0] == "حالت بازی: تنظیم نشده (پیش‌فرض ویندوز) ← روشن")
        chk("pattern with a drive", clean[1] == "فضای آزاد C:")
        chk("pattern with numbers keeps the numbers", clean[2] == "C:  275 GB آزاد از 476 GB (58٪ آزاد)")
        chk("n/a is translated", clean[3] == "نامعلوم")
        chk("two sentences, both translated", "بیشتر از حد پیشنهادی ما (8) است." in clean[5] and clean[5].startswith("برنامه‌هایی"))
        chk("low RAM finding", clean[6].startswith("کمبود RAM: 30 ثانیه"))
        chk("no entry: English stays (never empty)", clean[7] == "Untranslated English stays.")
        chk("a piece of a line gets no marks", "‏" not in out[8])
        chk("a Persian line is marked right-to-left", out[1].startswith("‏"))
        chk("'C:  275 GB' is kept in one piece", "⁦C:  275 GB⁩" in out[2])
        chk("a whole line from pieces is marked by Tr.line", out[9].startswith("‏") and "⁦275 GB⁩" in out[9])
        chk("English mode: untouched", out[10] == "Free space on C:")
except Exception as ex:
    chk("Qt JS check ran (%r)" % ex, False)

print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
