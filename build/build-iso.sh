#!/usr/bin/env bash
# Builds killday-os-<version>-<tier>.iso with live-build. Run inside the builder
# container: KD_TIER=lite build/kd builder build/build-iso.sh
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck source=build/config.sh
source build/config.sh

TIER="${KD_TIER:-${1:-lite}}"
validate_tier "$TIER"
export KD_TIER="$TIER"
[ -f "$KD_OUT/portal/index.html" ] || build/build-portal.sh

work="/build/$TIER"
mkdir -p "$work"
cd "$work"
lb clean >/dev/null 2>&1 || true  # Keeps the package cache between rebuilds.
lb config --mode debian --distribution "$KD_DISTRIBUTION" --architectures amd64 \
    --binary-images iso-hybrid --bootloaders "grub-efi,grub-pc" --debian-installer none \
    --archive-areas "main contrib non-free non-free-firmware" \
    --firmware-chroot true --firmware-binary false --memtest none \
    --linux-flavours amd64 --apt-recommends false \
    --chroot-squashfs-compression-type zstd \
    --iso-application "Kill-Day OS" --iso-publisher "Kill-Day OS" --iso-volume "KILLDAY_OS" \
    --bootappend-live "boot=live components" --cache-packages true

src="$KD_ROOT/build/live-build"
cp -R "$src/package-lists/." config/package-lists/
cp -R "$src/hooks/." config/hooks/
cp -R "$src/includes.chroot/." config/includes.chroot/

chroot_inc=config/includes.chroot
mkdir -p "$chroot_inc/usr/share/killday" "$chroot_inc/usr/lib/killday" "$chroot_inc/usr/share/backgrounds/killday" \
    "$chroot_inc/usr/local/share/fonts/killday" "$chroot_inc/usr/share/plymouth/themes" \
    "$chroot_inc/usr/share/icons/hicolor/256x256/apps" "$chroot_inc/srv/library" "$chroot_inc/etc/killday"
cp -R "$KD_OUT/portal" "$chroot_inc/usr/share/killday/portal"
cp "$KD_OUT/tools/linux-amd64/killday-serve" "$chroot_inc/usr/lib/killday/"
cp "$KD_ROOT/branding/wallpaper/killday-wallpaper.png" "$chroot_inc/usr/share/backgrounds/killday/"
cp "$KD_ROOT"/branding/fonts/*.ttf "$chroot_inc/usr/local/share/fonts/killday/"
cp -R "$KD_ROOT/branding/plymouth/killday" "$chroot_inc/usr/share/plymouth/themes/"
cp "$KD_ROOT/branding/png/killday-skull-256.png" "$chroot_inc/usr/share/icons/hicolor/256x256/apps/killday-skull.png"
printf 'KD_VERSION=%s\nKD_TIER=%s\nKD_BUILD_DATE=%s\n' "$KD_VERSION" "$TIER" "$(date -u +%F)" > "$chroot_inc/etc/killday/build-info"

mkdir -p config/killday config/includes.binary/.disk config/includes.binary/boot/grub/killday config/includes.binary/live
cp "$KD_ROOT/branding/grub/grub.cfg" config/killday/grub.cfg
cp -R "$KD_ROOT/branding/grub/theme/." config/includes.binary/boot/grub/killday/
touch config/includes.binary/.disk/killday-boot
cp /boot/memtest86+x64.bin /boot/memtest86+x64.efi config/includes.binary/live/

lb build 2>&1 | tee "$KD_OUT/lb-build-$TIER.log"

image=$(find . -maxdepth 1 -name "*.iso" | head -1)
[ -n "$image" ] || { echo "live-build produced no ISO." >&2; exit 1; }
target="$KD_OUT/killday-os-$KD_VERSION-$TIER.iso"
cp "$image" "$target"
(cd "$KD_OUT" && sha256sum "$(basename "$target")" > "$(basename "$target").sha256")
ls -lh "$target"
