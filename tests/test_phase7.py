import os as _os
import sys, io, contextlib, time
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
with contextlib.redirect_stdout(io.StringIO()):
    from t_helpers import load, boot, flush, OUT
ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

m = load()
def fake_json(cls, script):
    if "Get-PhysicalDisk" in script:
        return [{"DeviceId": "0", "FriendlyName": "Samsung SSD 980 1TB", "Media": "SSD", "Bus": "NVMe", "Health": "Healthy", "State": "OK", "Size": 1000204886016},
                {"DeviceId": "1", "FriendlyName": "WDC WD10EZEX", "Media": "HDD", "Bus": "SATA", "Health": "Warning", "State": "Degraded", "Size": 1000204886016},
                {"DeviceId": "2", "FriendlyName": "Mystery Disk", "Media": "Unspecified", "Bus": "USB", "Health": "", "State": "", "Size": 1}]
    if "Get-Partition" in script:
        return [{"DriveLetter": "C", "DiskNumber": 0}, {"DriveLetter": "D", "DiskNumber": 1}]
    return []
m.SystemInfo._json = classmethod(fake_json)
app = boot(m); tel = app.telemetry
tel.info._collect()
chk("2 mappings", tel.info.letter_disk == {"C": "0", "D": "1"} and len(tel.info.disks) == 3)
chk("kinds", [tel.info.disk_kind(d) for d in tel.info.disks] == ["NVMe SSD", "HDD", "USB"])
chk("disk_for C:\\", tel.info.disk_for("C:\\")["name"].startswith("Samsung") and tel.info.disk_for("Z:\\") is None)
tel.sensors.read = lambda: [("Storage", "Samsung SSD 980 1TB", "Temperature", "Temperature", 41.0),
                            ("Storage", "Samsung SSD 980 1TB", "Level", "Percentage Used", 3.0),
                            ("Storage", "Samsung SSD 980 1TB", "Data", "Unrelated", 9.0)]
rows = tel.rows_drive_health()
txt = [(r[1], r[2]) for r in rows if r[0] == "row"]
chk("healthy / warning shown with Windows text", ("Samsung SSD 980 1TB (NVMe SSD)", "Healthy") in txt and ("WDC WD10EZEX (HDD)", "Warning") in txt)
chk("SMART values only the useful ones", ("  Temperature", "41 °C") in txt and ("  Percentage Used", "3 %") in txt and not any("Unrelated" in a for a, _ in txt))
chk("drive without sensors says so, not 'healthy'", ("  Wear / SMART", "not provided by this drive") in txt)
chk("unknown health stays 'unknown'", ("Mystery Disk (USB)", "unknown") in txt)
chk("degraded status listed", ("  Status", "Degraded") in txt)
m.psutil.disk_partitions = lambda all=False: [type("P", (), dict(mountpoint="C:\\", opts="rw", fstype="NTFS"))()]
m.psutil.disk_usage = lambda mp: type("U", (), dict(total=100, used=50, free=50, percent=50.0))()
tel.storage._t = 0
srows = tel.rows_storage()
chk("drive bar names the type", any(r[0] == "bar" and "NVMe SSD" in r[1] for r in srows))
tel.info.disks = []; tel.info.ready = True
chk("no Windows answer -> n/a", ("row", "Drives", "n/a (Windows did not answer)") in tel.rows_drive_health())
# dashboard card
tel.info._collect = lambda: None
w = app.window; w.show(); flush(); tel.info.disks = [dict(id="0", name="Samsung SSD 980", media="SSD", bus="NVMe", health="Healthy", state="OK", size=1)]; tel.info.letter_disk = {"C": "0"}
tel.storage._t = 0; tel.storage.read(); app.sample_now(wait=True); w.show_page(0); app.sample_now(wait=True)
chk("dashboard storage card shows the type", "NVMe" in w.canvas.itemcget(w.gauges["disk"].sub2, "text"))
w.hw_tab = 2; w.show_page(2); w._apply_hw_tabs(); app.sample_now(wait=True); flush()
w.canvas.render(f"{OUT}/p7_storage.png")
print(f"phase7: {ok} ok, {bad} failed"); sys.exit(1 if bad else 0)
