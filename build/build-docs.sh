#!/usr/bin/env bash
# Regenerates the printable quick-start card and the USB label.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 branding/generate.py
python3 docs/make_quickstart.py
