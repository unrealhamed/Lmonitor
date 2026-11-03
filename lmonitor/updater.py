"""Update check against GitHub Releases (no UI imports).

latest()  -> info dict when a newer release with an installer exists, else None
download() saves the installer after checking host, size and (if given) SHA-256
install_command() is the command line that installs it silently and restarts Lmonitor
"""
import hashlib
import json
import os
import re
import urllib.request
from urllib.parse import urlparse

REPO = "unrealhamed/Lmonitor"
API = "https://api.github.com/repos/%s/releases/latest" % REPO


class UpdateError(Exception):
    pass


def parse_version(text):
    """'v1.15.3' / '1.15.3-dev' -> (1, 15, 3); anything else -> None."""
    m = re.match(r"v?(\d+(?:\.\d+)*)", str(text).strip())
    return tuple(int(n) for n in m.group(1).split(".")) if m else None


def _get(url, opener, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "Lmonitor"})
    return opener(req, timeout=timeout)


def latest(current, opener=urllib.request.urlopen):
    with _get(API, opener) as r:
        rel = json.loads(r.read().decode("utf-8"))
    new, old = parse_version(rel.get("tag_name", "")), parse_version(current)
    if rel.get("draft") or rel.get("prerelease") or not new or not old or new <= old:
        return None
    for a in rel.get("assets", []):
        url = a.get("browser_download_url", "")
        if re.fullmatch(r"Lmonitor_Setup_.+\.exe", a.get("name", "")) and urlparse(url).hostname == "github.com":
            digest = a.get("digest") or ""
            return {"version": ".".join(map(str, new)), "url": url, "name": a["name"],
                    "size": a.get("size"), "page": rel.get("html_url", ""),
                    "sha256": digest[7:] if digest.startswith("sha256:") else None}
    return None


def download(info, folder, opener=urllib.request.urlopen):
    path = os.path.join(folder, info["name"])
    part, h = path + ".part", hashlib.sha256()
    try:
        with _get(info["url"], opener, 60) as r, open(part, "wb") as f:
            for chunk in iter(lambda: r.read(1 << 16), b""):
                f.write(chunk)
                h.update(chunk)
        if info["size"] is not None and os.path.getsize(part) != info["size"]:
            raise UpdateError("Downloaded file has the wrong size")
        if info["sha256"] and h.hexdigest() != info["sha256"].lower():
            raise UpdateError("Downloaded file does not match its SHA-256")
        os.replace(part, path)
        return path
    finally:
        if os.path.exists(part):
            os.remove(part)


def install_command(setup, exe):
    """One cmd line: wait for Lmonitor to exit, install silently, start it again."""
    return 'ping -n 3 127.0.0.1 >nul & "%s" /SILENT /SUPPRESSMSGBOXES /NORESTART & start "" "%s"' % (setup, exe)
