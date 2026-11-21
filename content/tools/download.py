#!/usr/bin/env python3
"""Downloads and verifies the library. Resumable, and safe to re-run."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UA = "Mozilla/5.0 (X11; Linux x86_64) KillDayOS-manifest/1.0"
KIWIX_MIRROR = os.environ.get("KD_KIWIX_MIRROR", "https://ftp.fau.de/kiwix/")
BUDGET_GB = {"lite": 36, "plus": 82, "standard": 165, "full": 830}


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(1 << 22):
            digest.update(chunk)
    return digest.hexdigest()


def candidates(url):
    """Tries a fast mirror first. The checksum protects against a bad mirror."""
    official = "https://download.kiwix.org/"
    if url.startswith(official):
        return [url.replace(official, KIWIX_MIRROR), url]
    return [url]


def fetch(url, target, expected):
    """Resumes into <target>.part and only keeps the file if its hash matches."""
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    for source in candidates(url):
        subprocess.run(["curl", "-fL", "-C", "-", "--retry", "20", "--retry-delay", "10", "--retry-all-errors",
                        "-A", UA, "-o", str(partial), source], check=False)
        if partial.exists() and sha256_of(partial) == expected:
            partial.replace(target)
            return True
        print(f"Bad or incomplete download from {source}: {target.name}", file=sys.stderr)
        partial.unlink(missing_ok=True)
    return False


def extract_map(item, target, tool):
    target.parent.mkdir(parents=True, exist_ok=True)
    bbox = ",".join(str(v) for v in item["bbox"])
    partial = target.with_name(target.name + ".part")
    if item.get("whole_planet"):
        subprocess.run(["curl", "-fL", "-C", "-", "--retry", "20", "--retry-all-errors", "-o", str(partial), item["url"]], check=True)
        subprocess.run([str(tool), "verify", str(partial)], check=True)
        partial.replace(target)
        return
    subprocess.run([str(tool), "extract", item["url"], str(partial), f"--bbox={bbox}",
                    f"--maxzoom={item['maxzoom']}", "--download-threads=4"], check=True)
    subprocess.run([str(tool), "verify", str(partial)], check=True)
    partial.replace(target)


def install_tool(tool_item, staging):
    if tool_item["platform"] == "build":
        return
    destination = staging / "tools" / tool_item["platform"]
    binary = "kiwix-serve.exe" if "windows" in tool_item["platform"] else "kiwix-serve"
    if tool_item.get("optional"):
        binary = "llama-cli"
    if (destination / binary).exists():
        return
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "archive"
        if not fetch(tool_item["url"], archive, tool_item["sha256"]):
            raise SystemExit(f"Could not download {tool_item['title']}")
        destination.mkdir(parents=True, exist_ok=True)
        extracted = Path(tmp) / "x"
        if tool_item["url"].endswith(".zip"):
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(extracted)
        else:
            with tarfile.open(archive) as bundle:
                bundle.extractall(extracted, filter="data")
        for found in extracted.rglob("*"):
            if found.is_file():
                shutil.copy(found, destination / found.name)
                (destination / found.name).chmod(0o755)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", default="lite", choices=BUDGET_GB)
    parser.add_argument("--modules", help="comma-separated module ids (default: all)")
    parser.add_argument("--only", help="comma-separated item ids, for testing")
    parser.add_argument("--staging", default=str(ROOT / "out" / "library"))
    parser.add_argument("--list", action="store_true", help="show what would be fetched, then stop")
    parser.add_argument("--with-optional", action="store_true", help="include the optional AI model")
    args = parser.parse_args()

    manifest = json.loads((ROOT / "content" / "manifest.json").read_text())
    staging = Path(args.staging)
    wanted = set(args.modules.split(",")) if args.modules else None
    unknown = (wanted or set()) - {m["id"] for m in manifest["modules"]}
    if unknown:
        raise SystemExit(f"Unknown module(s): {', '.join(sorted(unknown))}")

    chosen = [(m, i) for m in manifest["modules"] for i in m["items"]
              if args.tier in i["tiers"] and (wanted is None or m["id"] in wanted)
              and (args.with_optional or not i.get("optional"))]
    if args.only:
        ids = set(args.only.split(","))
        chosen = [(m, i) for m in manifest["modules"] for i in m["items"] if i["id"] in ids]
    total = sum(i["size"] for _, i in chosen) / 1e9
    for module, item in chosen:
        print(f"{module['id']:14} {item['size'] / 1e9:9.2f} GB  {item['title']}  [{item['license']}]")
    print(f"Total {total:.1f} GB for tier {args.tier} (budget {BUDGET_GB[args.tier]} GB)")
    if args.list:
        return
    if total > BUDGET_GB[args.tier]:
        raise SystemExit("This selection is larger than the tier allows. Use --modules to pick fewer.")
    free = shutil.disk_usage(staging if staging.exists() else staging.parent).free / 1e9
    if total > free:
        print(f"Warning: only {free:.0f} GB free in the staging area.", file=sys.stderr)

    tool_path = ROOT / "out" / "cache" / "bin" / "pmtiles"
    installed, failed = [], []
    for module, item in chosen:
        target = staging / item["path"]
        if item["kind"] == "map":
            if not target.exists():
                try:
                    extract_map(item, target, tool_path)
                except subprocess.CalledProcessError as err:
                    failed.append(item["title"])
                    print(f"Map failed: {err}", file=sys.stderr)
                    continue
            entry = {**item, "sha256": sha256_of(target), "size": target.stat().st_size}
        else:
            if target.exists() and target.stat().st_size == item["size"] and sha256_of(target) == item["sha256"]:
                print(f"verified  {target.name}")
            elif not fetch(item["url"], target, item["sha256"]):
                failed.append(item["title"])
                continue
            entry = item
        installed.append({"module": module["id"], **entry})

    for tool_item in manifest["tools"]:
        if args.with_optional or not tool_item.get("optional"):
            install_tool(tool_item, staging)

    (staging / "manifest").mkdir(parents=True, exist_ok=True)
    (staging / "manifest" / "installed.json").write_text(json.dumps(
        {"tier": args.tier, "last_verified": manifest["last_verified"], "items": installed}, indent=1))
    if failed:
        print("Failed:\n  " + "\n  ".join(failed), file=sys.stderr)
        raise SystemExit(1)
    print("Library staged and verified. Corrupted? Still alive.")


if __name__ == "__main__":
    main()
