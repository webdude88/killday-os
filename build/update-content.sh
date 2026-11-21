#!/usr/bin/env bash
# Refreshes ZIMs, documents and maps on an existing library when you have internet.
# Usage: update-content.sh --library /path/to/KILLDAY_LIB --tier TIER [--modules a,b]
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck source=build/config.sh
source build/config.sh

library="" tier="" modules=()
while [ $# -gt 0 ]; do
    case "$1" in
        --library) library="$2"; shift 2 ;;
        --tier) tier="$2"; shift 2 ;;
        --modules) modules=(--modules "$2"); shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
done
validate_tier "$tier"
[ -w "$library/manifest" ] || { echo "$library is not a writable Kill-Day library." >&2; exit 1; }

python3 content/tools/resolve_manifest.py --staging "$library"
# Maps are extracted from a dated planet build, so refreshing means replacing them.
rm -f "$library"/maps/*.pmtiles
python3 content/tools/download.py --tier "$tier" --staging "$library" "${modules[@]}"

# Only delete old ZIMs after the new set downloaded and verified above.
python3 - "$library" <<'PY'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
keep = {item["path"] for item in json.loads((root / "manifest/installed.json").read_text())["items"]}
for old in (root / "zim").glob("*.zim"):
    if f"zim/{old.name}" not in keep:
        print("removing superseded", old.name)
        old.unlink()
PY
KD_STAGING="$library" KD_TIER="$tier" build/build-library.sh
