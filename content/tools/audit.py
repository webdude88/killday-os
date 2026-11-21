#!/usr/bin/env python3
"""Checks a library against its installed manifest. Exit status 1 means damage."""
import hashlib
import json
import sys
from pathlib import Path


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(1 << 22):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    manifest_path = root / "manifest" / "installed.json"
    if not manifest_path.exists():
        print(f"No installed manifest at {manifest_path}.")
        return 2
    items = json.loads(manifest_path.read_text())["items"]
    good, missing, corrupt = 0, [], []
    for item in items:
        path = root / item["path"]
        if not path.exists():
            missing.append(item["path"])
            status = "MISSING"
        elif path.stat().st_size != item["size"] or sha256_of(path) != item["sha256"]:
            corrupt.append(item["path"])
            status = "CORRUPT"
        else:
            good += 1
            status = "ok"
        print(f"{status:8} {item['path']}")
    print(f"\n{good} good, {len(missing)} missing, {len(corrupt)} corrupted, of {len(items)} files.")
    if missing or corrupt:
        print("The library is damaged. Re-run build/download-content.sh, or restore these files from another copy.")
        return 1
    print("Corrupted? Not this time. Library is intact.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
