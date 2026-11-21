#!/usr/bin/env python3
"""Creates small HTML pages holding each guide's text so Pagefind can index it.

The stubs are search data only. Results link to the reader page, which shows
the safety disclaimer, rather than to the stubs themselves.
"""
import html
import json
import re
import subprocess
import sys
from pathlib import Path

PAGES_PER_STUB = 4


def write_stub(out, name, title, target, source, warn, text):
    body = html.escape(text)
    out.joinpath(f"{name}.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f'<title>{html.escape(title)}</title></head><body data-pagefind-body>'
        f'<span data-pagefind-meta="title">{html.escape(title)}</span>'
        f'<span data-pagefind-meta="target:{html.escape(target, quote=True)}"></span>'
        f'<span data-pagefind-meta="source:{html.escape(source, quote=True)}"></span>'
        f'<span data-pagefind-meta="warn:{warn}"></span><p>{body}</p></body></html>', encoding="utf-8")


def index_pdf(path, item, out, warn):
    text = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True).stdout.decode("utf-8", "ignore")
    pages = text.split("\f")
    for start in range(0, len(pages), PAGES_PER_STUB):
        chunk = " ".join(pages[start:start + PAGES_PER_STUB]).strip()
        if len(chunk) < 40:
            continue
        page = start + 1
        target = f"read.html?id={item['id']}#page={page}"
        write_stub(out, f"{item['id']}-{page}", f"{item['title']}, page {page}", target, item["source"], warn, re.sub(r"\s+", " ", chunk))


def index_html(path, item, out, warn):
    raw = path.read_text("utf-8", "ignore")
    text = re.sub(r"(?is)<(script|style).*?</\1>|<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", html.unescape(text))
    size = 6000
    for number, start in enumerate(range(0, len(text), size)):
        write_stub(out, f"{item['id']}-{number}", item["title"], f"read.html?id={item['id']}", item["source"], warn, text[start:start + size])


def main():
    library, catalog_path = Path(sys.argv[1]), Path(sys.argv[2])
    out = library / "almanac" / "_search"
    out.mkdir(parents=True, exist_ok=True)
    catalog = json.loads(catalog_path.read_text())
    for module in catalog["modules"]:
        for item in module["items"]:
            path = library / (item.get("path") or "")
            if not item.get("path") or not path.exists():
                continue
            kind = item.get("disclaimer") or module.get("disclaimer") or ""
            warn = "yes" if kind and kind != "general" else "no"
            if item["kind"] == "pdf":
                index_pdf(path, item, out, warn)
            elif item["kind"] == "html":
                index_html(path, item, out, warn)


if __name__ == "__main__":
    main()
