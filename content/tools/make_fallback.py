#!/usr/bin/env python3
"""Writes START-HERE.html, which works with no server at all.

If nothing can run on the host, a double-click still reaches every document.
"""
import html
import json
import sys
from pathlib import Path


def main():
    library, catalog_path = Path(sys.argv[1]), Path(sys.argv[2])
    catalog = json.loads(catalog_path.read_text())
    sections = []
    for module in catalog["modules"]:
        rows = []
        for item in module["items"]:
            if item["kind"] in ("pdf", "html") and (library / item["path"]).exists():
                rows.append(f'<li><a href="{html.escape(item["path"])}">{html.escape(item["title"])}</a></li>')
        if rows:
            warning = catalog["disclaimers"].get(module.get("disclaimer") or "")
            box = f'<p class="w">{html.escape(warning)}</p>' if warning else ""
            sections.append(f'<h2>{html.escape(module["title"])}</h2>{box}<ul>{"".join(rows)}</ul>')
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kill-Day OS: Start here</title><style>
body{{background:#0B0F0C;color:#E6EBE0;font:18px/1.55 sans-serif;margin:0 auto;max-width:48rem;padding:24px}}
a{{color:#8CFF5A}}h1,h2{{color:#8CFF5A}}.w{{background:#3a0d13;border-left:5px solid #FF3B4E;padding:12px 16px;color:#fff;font-weight:600}}
</style></head><body><h1>KILL-DAY OS</h1><p>Corrupted? Still alive.</p>
<p><strong>For search, maps and encyclopedias:</strong> close this page and run START-WINDOWS (Windows) or START-MAC (Mac) from this drive.</p>
<p>If those will not run, every guide below still opens directly. Encyclopedia files in the zim folder can be opened with the free Kiwix app.</p>
{"".join(sections)}</body></html>"""
    (library / "START-HERE.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    main()
