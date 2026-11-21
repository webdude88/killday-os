#!/usr/bin/env python3
"""Reduces the manifest to the catalog the portal reads for one tier."""
import json
import sys
from pathlib import Path


def main():
    manifest = json.loads(Path(sys.argv[1]).read_text())
    tier = sys.argv[3]
    fields = ("id", "title", "kind", "path", "license", "source", "description", "disclaimer")
    modules = []
    for module in manifest["modules"]:
        items = [{k: item.get(k) for k in fields} for item in module["items"] if tier in item["tiers"]]
        if items:
            modules.append({**{k: module[k] for k in ("id", "title", "blurb", "disclaimer")}, "items": items})
    Path(sys.argv[2]).write_text(json.dumps({"disclaimers": manifest["disclaimers"], "modules": modules}, indent=1))


if __name__ == "__main__":
    main()
