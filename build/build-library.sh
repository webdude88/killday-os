#!/usr/bin/env bash
# Turns downloaded content into a finished library: portal, search index,
# launchers and a fallback page. Run after download-content.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck source=build/config.sh
source build/config.sh

TIER="${KD_TIER:-${1:-lite}}"
validate_tier "$TIER"
export KD_TIER="$TIER"
build/build-portal.sh
library="$KD_STAGING"
mkdir -p "$library/tools"

rm -rf "$library/almanac"
cp -R "$KD_OUT/portal" "$library/almanac"
for platform in linux-amd64 windows-amd64 darwin-amd64 darwin-arm64; do
    mkdir -p "$library/tools/$platform"
    cp "$KD_OUT/tools/$platform/"killday-serve* "$library/tools/$platform/"
done

echo "== Building the search index"
python3 content/tools/make_search_stubs.py "$library" "$library/almanac/catalog.json"
"$KD_OUT/cache/vendor/node_modules/.bin/pagefind" --site "$library/almanac" --output-subdir pagefind --glob '{_search/**/*.html,start-here.html,rescue.html}'
# The index holds the text now, and read.html is what readers should land on.
rm -rf "$library/almanac/_search"

cp docs/launchers/START-WINDOWS.bat docs/launchers/START-MAC.command docs/launchers/START-LINUX.sh "$library/"
python3 content/tools/make_fallback.py "$library" "$library/almanac/catalog.json"
[ -f "$library/manifest/installed.json" ] && python3 content/tools/audit.py "$library"
echo "Library ready at $library"
