#!/usr/bin/env bash
# Regenerates every branding asset from the skull SVG. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 branding/generate.py
