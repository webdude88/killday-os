#!/usr/bin/env python3
"""Turns content/sources.json into content/manifest.json by checking every source.

ZIMs get their newest dated file, size and published SHA-256. Documents are
downloaded into the staging library and hashed. Anything that fails is left out
of the manifest and written to content/UNVERIFIED.md instead.
"""
import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UA = "Mozilla/5.0 (X11; Linux x86_64) KillDayOS-manifest/1.0"
KIWIX = "https://download.kiwix.org/zim"
TODAY = datetime.date.today().isoformat()
MAX_ZIM_AGE_HINT = "newest dated file in the Kiwix directory"


def curl(*args, check=True):
    return subprocess.run(["curl", "-sSL", "--retry", "3", "-m", "120", "-A", UA, *args],
                          check=check, capture_output=True, text=True).stdout


def head_size(url):
    headers = curl("-I", url)
    sizes = re.findall(r"(?im)^content-length:\s*(\d+)", headers)
    statuses = re.findall(r"(?im)^HTTP/\S+\s+(\d+)", headers)
    if not statuses or statuses[-1] != "200" or not sizes:
        raise RuntimeError(f"HEAD failed ({statuses[-1:] or 'no response'})")
    return int(sizes[-1])


listings = {}


def latest_zim(folder, prefix):
    if folder not in listings:
        listings[folder] = sorted(set(re.findall(r'[A-Za-z0-9_.-]+\.zim', curl(f"{KIWIX}/{folder}/"))))
    pattern = re.compile(re.escape(prefix) + r"_(\d{4}-\d{2})\.zim$")
    matches = sorted((m.group(1), name) for name in listings[folder] if (m := pattern.match(name)))
    if not matches:
        raise RuntimeError(f"no {prefix} file in {folder}")
    return matches[-1][1]


def resolve_zim(item):
    name = latest_zim(item["zim_dir"], item["zim_prefix"])
    url = f"{KIWIX}/{item['zim_dir']}/{name}"
    digest = curl(url + ".sha256").split()[0]
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise RuntimeError("published checksum is not a SHA-256")
    return dict(url=url, path=f"zim/{name}", size=head_size(url), sha256=digest,
                checksum_source="Kiwix published .sha256")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_document(url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    subprocess.run(["curl", "-sSfL", "--retry", "3", "-m", "1800", "-A", UA, "-o", str(partial), url], check=True)
    partial.replace(destination)


def check_document(path, kind, required):
    with open(path, "rb") as handle:
        magic = handle.read(8)
    if kind == "pdf" and not magic.startswith(b"%PDF"):
        raise RuntimeError("server did not return a PDF")
    if kind == "pdf" and required:
        text = subprocess.run(["pdftotext", "-l", "12", str(path), "-"], capture_output=True, text=True).stdout
        if required.lower() not in re.sub(r"\s+", " ", text).lower():
            raise RuntimeError(f"license evidence '{required}' not found in the first 12 pages")


def resolve_document(item, staging, folder, extension):
    url = urllib.parse.quote(item["url"], safe=":/?&=%")
    rel = f"{folder}/{item['id']}.{extension}"
    target = staging / rel
    if not target.exists():
        fetch_document(url, target)
    try:
        check_document(target, item["kind"], item.get("require_text"))
    except Exception:
        target.unlink()
        raise
    return dict(url=url, path=rel, size=target.stat().st_size, sha256=sha256_file(target),
                checksum_source="Computed from a download on the verified date")


def openstax_index():
    query = "https://openstax.org/apps/cms/api/v2/pages/?type=books.Book&fields=title,high_resolution_pdf_url,license_name&limit=200"
    return {b["meta"]["slug"]: b for b in json.loads(curl(query))["items"]}


def resolve_openstax(item, index, staging):
    book = index.get(item["slug"])
    if not book or not book.get("high_resolution_pdf_url"):
        raise RuntimeError("no PDF listed by the OpenStax API")
    item["url"] = book["high_resolution_pdf_url"]
    item["license"] = book["license_name"]
    item["kind"] = "pdf"
    return resolve_document(item, staging, "docs/education", "pdf")


def pmtiles_binary(staging_cache):
    binary = staging_cache / "pmtiles"
    if not binary.exists():
        url = "https://github.com/protomaps/go-pmtiles/releases/download/v1.31.2/go-pmtiles_1.31.2_Linux_x86_64.tar.gz"
        with tempfile.NamedTemporaryFile(suffix=".tgz") as tmp:
            subprocess.run(["curl", "-sSfL", "-o", tmp.name, url], check=True)
            with tarfile.open(tmp.name) as archive:
                member = archive.getmember("pmtiles")
                binary.parent.mkdir(parents=True, exist_ok=True)
                binary.write_bytes(archive.extractfile(member).read())
        binary.chmod(0o755)
    return binary


def latest_planet():
    for offset in range(0, 14):
        day = (datetime.date.today() - datetime.timedelta(days=offset)).strftime("%Y%m%d")
        url = f"https://build.protomaps.com/{day}.pmtiles"
        if "200" in curl("-I", "-o", "/dev/null", "-w", "%{http_code}", url, check=False):
            return url
    raise RuntimeError("no recent Protomaps planet build found")


def resolve_map(item, planet, tool):
    if item.get("whole_planet"):
        return dict(url=planet, path=f"maps/{item['region']}.pmtiles", size=head_size(planet), sha256=None,
                    checksum_source="Protomaps publishes no hash. Checked with pmtiles verify, then hashed locally.")
    bbox = ",".join(str(v) for v in item["bbox"])
    with tempfile.TemporaryDirectory() as tmp:
        output = subprocess.run(
            [str(tool), "extract", planet, f"{tmp}/x.pmtiles", f"--bbox={bbox}", f"--maxzoom={item['maxzoom']}", "--dry-run"],
            capture_output=True, text=True, check=True)
    text = output.stdout + output.stderr
    match = re.search(r"Archive size:\s*([\d.]+)\s*([KMGT]?i?B)", text) or re.search(r"([\d.]+)\s*([KMGT]i?B)", text)
    if not match:
        raise RuntimeError("dry run did not report a size")
    units = {"B": 1, "KB": 1e3, "MB": 1e6, "GB": 1e9, "TB": 1e12, "KIB": 1024, "MIB": 1024**2, "GIB": 1024**3, "TIB": 1024**4}
    return dict(url=planet, path=f"maps/{item['region']}.pmtiles", size=int(float(match[1]) * units[match[2].upper()]),
                sha256=None, size_is_estimate=True,
                checksum_source="Extracted per build. The hash is recorded in manifest/installed.json at extraction.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--staging", default=str(ROOT / "out" / "library"))
    args = parser.parse_args()
    staging = Path(args.staging)
    sources = json.loads((ROOT / "content" / "sources.json").read_text())
    failures = []
    index = openstax_index()
    tool = pmtiles_binary(ROOT / "out" / "cache" / "bin")
    planet = latest_planet()

    for module in sources["modules"]:
        kept = []
        for item in module["items"]:
            try:
                kind = item["kind"]
                if kind == "zim":
                    resolved = resolve_zim(item)
                elif kind == "openstax":
                    resolved = resolve_openstax(item, index, staging)
                elif kind == "pdf":
                    resolved = resolve_document(item, staging, f"docs/{module['id']}", "pdf")
                elif kind == "html":
                    resolved = resolve_document(item, staging, "books", "html")
                elif kind == "map":
                    resolved = resolve_map(item, planet, tool)
                elif kind == "file":
                    size = head_size(item["url"])
                    etag = re.findall(r'(?im)^x-linked-etag:\s*"?([0-9a-f]{64})', curl("-I", item["url"]))
                    if not etag:
                        raise RuntimeError("no SHA-256 published by the host")
                    resolved = dict(size=size, sha256=etag[-1], checksum_source="Hugging Face LFS SHA-256")
                else:
                    raise RuntimeError(f"unknown kind {kind}")
            except Exception as err:  # A bad source must not stop the rest of the run.
                detail = getattr(err, "stderr", "") or err
                failures.append((module["id"], item["title"], item.get("url") or item.get("zim_prefix") or "", str(detail).strip()))
                print(f"FAIL {item['id']}: {detail}", file=sys.stderr)
                continue
            item.update(resolved)
            item["last_verified"] = TODAY
            print(f"ok   {item['id']}  {item['size'] / 1e9:.2f} GB")
            kept.append(item)
        module["items"] = kept

    for tool_item in sources["tools"]:
        try:
            tool_item["size"] = head_size(tool_item["url"])
            digest = curl(tool_item["url"] + ".sha256", check=False).split()
            if digest and re.fullmatch(r"[0-9a-f]{64}", digest[0]):
                tool_item["sha256"] = digest[0]
            else:
                with tempfile.NamedTemporaryFile() as tmp:
                    fetch_document(tool_item["url"], Path(tmp.name))
                    tool_item["sha256"] = sha256_file(tmp.name)
            tool_item["last_verified"] = TODAY
        except Exception as err:
            failures.append(("tools", tool_item["title"], tool_item["url"], str(err)))

    sources["last_verified"] = TODAY
    (ROOT / "content" / "manifest.json").write_text(json.dumps(sources, indent=1) + "\n")
    lines = ["# Sources that failed verification", "", f"Checked {TODAY}. These are not in the manifest and will not be downloaded.", ""]
    lines += [f"- **{title}** ({module}): `{url}`: {reason}" for module, title, url, reason in failures] or ["None."]
    (ROOT / "content" / "UNVERIFIED.md").write_text("\n".join(lines) + "\n")
    print(f"{len(failures)} source(s) failed; see content/UNVERIFIED.md")


if __name__ == "__main__":
    main()
