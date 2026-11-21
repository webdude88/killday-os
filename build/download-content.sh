#!/usr/bin/env bash
# Downloads the library into out/library. Examples:
#   build/download-content.sh --tier lite --list
#   build/download-content.sh --tier standard --modules medical,water,maps
set -euo pipefail
exec python3 "$(dirname "$0")/../content/tools/download.py" "$@"
