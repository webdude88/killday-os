#!/usr/bin/env bash
# Verifies a library against its manifest. Usage: audit-library.sh [LIBRARY_ROOT]
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$here/../content/tools/audit.py" "${1:-$here/../out/library}"
