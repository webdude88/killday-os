#!/usr/bin/env bash
# Assembles the static Almanac and cross-compiles killday-serve into out/portal.
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck source=build/config.sh
source build/config.sh

TIER="${KD_TIER:-lite}"
validate_tier "$TIER"
dist="$KD_OUT/portal"
vendor_cache="$KD_OUT/cache/vendor"
tools="$KD_OUT/tools"
mkdir -p "$dist/vendor" "$dist/fonts" "$dist/img" "$vendor_cache" "$tools"

cp -R portal/src/. "$dist/"
cp branding/fonts/*.ttf "$dist/fonts/"
cp branding/png/killday-skull-128.png branding/png/favicon.ico "$dist/img/"
python3 content/tools/make_catalog.py content/manifest.json "$dist/catalog.json" "$TIER"
jq -n --arg v "$KD_VERSION" --arg t "$TIER" --arg d "$(date -u +%Y-%m-%d)" \
    --arg c "$(jq -r '.last_verified' content/manifest.json)" \
    '{version:$v,tier:$t,build_date:$d,content_verified:$c}' > "$dist/build-info.json"

# Exact versions keep the bundled viewer reproducible.
if [ ! -f "$vendor_cache/.done" ]; then
    (cd "$vendor_cache" && npm init -y >/dev/null &&
        npm install --no-audit --no-fund maplibre-gl@5.6.2 pmtiles@4.3.0 @protomaps/basemaps@5.7.0 pagefind@1.3.0 >/dev/null)
    curl -fsSL -o "$vendor_cache/assets.tar.gz" https://github.com/protomaps/basemaps-assets/archive/refs/heads/main.tar.gz
    mkdir -p "$vendor_cache/assets"
    tar -xzf "$vendor_cache/assets.tar.gz" -C "$vendor_cache/assets" --strip-components=1
    touch "$vendor_cache/.done"
fi
modules="$vendor_cache/node_modules"
cp "$modules/maplibre-gl/dist/maplibre-gl.js" "$modules/maplibre-gl/dist/maplibre-gl.css" "$dist/vendor/"
cp "$modules/pmtiles/dist/pmtiles.js" "$dist/vendor/"
cp "$modules/@protomaps/basemaps/dist/basemaps.js" "$dist/vendor/"
assets="$dist/vendor/map-assets"
mkdir -p "$assets/fonts" "$assets/sprites"
for face in "Noto Sans Regular" "Noto Sans Medium" "Noto Sans Italic"; do
    cp -R "$vendor_cache/assets/fonts/$face" "$assets/fonts/"
done
cp -R "$vendor_cache/assets/sprites/v4" "$assets/sprites/"

for target in linux/amd64 windows/amd64 darwin/amd64 darwin/arm64; do
    goos="${target%/*}"; goarch="${target#*/}"
    ext=""; [ "$goos" = windows ] && ext=".exe"
    mkdir -p "$tools/$goos-$goarch"
    (cd portal/server && CGO_ENABLED=0 GOOS="$goos" GOARCH="$goarch" GOCACHE=/tmp/gocache \
        go build -trimpath -ldflags="-s -w" -o "$tools/$goos-$goarch/killday-serve$ext" .)
done
du -sh "$dist" "$tools"
