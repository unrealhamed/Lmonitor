"""Writes the Windows "version" resource used by PyInstaller.

usage: python tools/make_version.py <engine.py> <output.txt>
The version comes from AppInfo.VERSION in lmonitor/engine.py (single source of truth).
"""
import re
import sys


def read(src, name, default=""):
    m = re.search(r"^\s*%s\s*=\s*[\"']([^\"']*)[\"']" % name, src, re.M)
    return m.group(1) if m else default


def main():
    src = open(sys.argv[1], encoding="utf-8").read()
    name = read(src, "NAME", "Lmonitor")
    ver = read(src, "VERSION", "1.0.0")
    who = read(src, "PUBLISHER", "") or name
    nums = [int(x) for x in re.findall(r"\d+", ver)][:4]
    nums += [0] * (4 - len(nums))
    t = tuple(nums)
    text = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={t}, prodvers={t}, mask=0x3f, flags=0x0,
                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', '{who}'),
      StringStruct('FileDescription', '{name} - gaming overlay and system monitor'),
      StringStruct('FileVersion', '{ver}'),
      StringStruct('InternalName', '{name}'),
      StringStruct('OriginalFilename', '{name}.exe'),
      StringStruct('ProductName', '{name}'),
      StringStruct('ProductVersion', '{ver}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    open(sys.argv[2], "w", encoding="utf-8").write(text)
    print(ver)


main()
