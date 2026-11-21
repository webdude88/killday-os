#!/usr/bin/env bash
# Writes a Kill-Day USB from a Mac, where Docker cannot see USB drives. The real
# writer lays everything out in an image file, then this copies it to the stick.
# Usage: build/usb-from-mac.sh --device diskN [--tier lite|plus|standard|full] [--library DIR] [--reuse-image | --verify-only]
# --reuse-image skips the full build and uses a finished image, such as one prepared
# ahead of time. Its encrypted partition is always re-created with your passphrase.
# --verify-only writes nothing. It checks a stick that was already written against
# the image still in out/, for when the check after the copy was cut short.
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck source=build/config.sh
source build/config.sh

device="" tier="lite" reuse="no" verify_only="no" library="out/library"
while [ $# -gt 0 ]; do
    case "$1" in
        --device) device="${2#/dev/}"; shift 2 ;;
        --tier) tier="$2"; shift 2 ;;
        --reuse-image) reuse="yes"; shift ;;
        --verify-only) verify_only="yes"; shift ;;
        --library) library="${2%/}"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
done

fail() { echo "Refusing: $*" >&2; exit 1; }
disk_field() { diskutil info -plist "$1" 2>/dev/null | plutil -extract "$2" raw -o - - 2>/dev/null || true; }
fingerprint() { echo "$(disk_field "$device" MediaName)|$(disk_field "$device" TotalSize)|$(disk_field "$device" DeviceTreePath)"; }
parent_of_path() { disk_field "$(df "$1" | tail -1 | awk '{print $1}')" ParentWholeDisk; }

[ "$(uname -s)" = "Darwin" ] || fail "this script is for macOS. On Linux, use build/kd usb."
validate_tier "$tier"
[[ "$device" =~ ^disk[0-9]+$ ]] || fail "--device must be a whole disk, like disk6."

# Every check has to positively pass, so a missing answer stops the write.
[ "$(disk_field "$device" WholeDisk)" = "true" ] || fail "$device is not a whole disk that macOS can describe."
[ "$(disk_field "$device" Internal)" = "false" ] || fail "$device is an internal disk."
[ "$(disk_field "$device" BusProtocol)" = "USB" ] || fail "$device is not a USB device."
[ "$(disk_field "$device" VirtualOrPhysical)" = "Physical" ] || fail "$device is not a physical disk."
[ "$(disk_field "$device" RemovableMedia)" = "true" ] || fail "$device is a fixed drive, not a removable stick."
[ "$(parent_of_path /)" != "$device" ] || fail "$device holds the running system."
[ "$(parent_of_path "$PWD")" != "$device" ] || fail "$device holds this project."

size_bytes=$(disk_field "$device" TotalSize)
[[ "$size_bytes" =~ ^[0-9]+$ ]] || fail "could not read the size of $device."
min_gb=$(tier_setting "$tier" min_gb)
[ "$size_bytes" -ge $((min_gb * 1000000000)) ] || fail "the $tier tier needs at least $min_gb GB, and $device is smaller."

iso="out/killday-os-$KD_VERSION-$tier.iso"
image="out/killday-usb-$tier.img"
[ -f "$iso" ] || fail "$iso is missing."
case "$library" in /*|..*) fail "--library must be a folder inside the project, like out/library-plus." ;; esac
[ -f "$library/manifest/installed.json" ] || fail "the library is not built. Run download.py and build-library.sh first."
[ -d "$library/almanac" ] || fail "the library is not built. Run build-library.sh first."
docker image inspect killday-builder >/dev/null 2>&1 || fail "the builder image is missing. Run build/kd images."

# GiB, because that is what the writer's --size-gb means.
size_gb=$((size_bytes / 1073741824))
live_start=$((1 + $(tier_setting "$tier" boot)))
library_start=$((live_start + $(tier_setting "$tier" live) + $(tier_setting "$tier" persist)))
library_room_mb=$((size_gb * 1024 - 1 - library_start))
library_used_mb=$(($(du -sk "$library" | awk '{print $1}') / 1024))
[ $((library_used_mb + 512)) -le "$library_room_mb" ] || fail "the library needs $library_used_mb MiB, and this stick has room for $library_room_mb MiB."
if [ "$reuse" = "yes" ] || [ "$verify_only" = "yes" ]; then
    [ "$(stat -f %z "$image" 2>/dev/null || echo 0)" = "$((size_gb * 1073741824))" ] || fail "there is no finished $image of the right size to use."
fi

# The check that follows a copy, also used on its own by --verify-only.
verify_stick() {
    echo "== Checking what was written"
    # macOS may mount the FAT and exFAT partitions and add its own files, so those
    # are checked through their contents below, and the rest byte for byte.
    diskutil unmountDisk "/dev/$device" >/dev/null || true
    same_region() {
        cmp <(sudo dd if="/dev/r$device" bs=1m skip="$1" count="$2" 2>/dev/null) <(dd if="$image" bs=1m skip="$1" count="$2" 2>/dev/null)
    }
    same_region 0 1 || { echo "The start of the stick does not match the image." >&2; exit 1; }
    same_region "$live_start" "$((library_start - live_start))" || { echo "The system partitions do not match the image." >&2; exit 1; }
    diskutil mountDisk "/dev/$device" >/dev/null || true
    for _ in $(seq 1 30); do
        [ -d "/Volumes/$KD_LABEL_LIBRARY/manifest" ] && break
        sleep 1
    done
    [ -d "/Volumes/$KD_LABEL_LIBRARY/manifest" ] || { echo "The library partition did not mount, so it could not be checked." >&2; exit 1; }
    python3 content/tools/audit.py "/Volumes/$KD_LABEL_LIBRARY"
}

if [ "$verify_only" = "yes" ]; then
    echo "Checking /dev/$device ($(disk_field "$device" IORegistryEntryName), $((size_bytes / 1000000000)) GB). Nothing will be written."
    echo "Your Mac password is needed to read the stick."
    sudo -v
    verify_stick
    rm -f "$image"
    diskutil eject "/dev/$device"
    echo "Done. Corrupted? Still alive. You can unplug the stick."
    exit 0
fi

echo
echo "Target:  /dev/$device"
echo "Model:   $(disk_field "$device" IORegistryEntryName)"
echo "Size:    $((size_bytes / 1000000000)) GB"
echo
diskutil list "$device"
echo "EVERYTHING on this drive will be erased. This cannot be undone."
typed=""
read -r -p "Type the device name ($device) to continue: " typed || true
[ "$typed" = "$device" ] || { echo "That did not match. Nothing was changed."; exit 1; }
identity=$(fingerprint)

keepalive="" finished="no" built="no"
cleanup() {
    [ -z "$keepalive" ] || kill "$keepalive" 2>/dev/null || true
    if [ "$finished" != "yes" ] && [ "$built" = "yes" ]; then
        echo "Stopped early, but the image is finished. To carry on without rebuilding:" >&2
        echo "  build/usb-from-mac.sh --device $device --tier $tier --library $library --reuse-image" >&2
    elif [ "$finished" != "yes" ] && [ -e "$image" ]; then
        echo "Stopped early. A partial image is at $image, and the next run replaces it." >&2
    fi
}
trap cleanup EXIT

echo "Your Mac password is needed for the copy at the end."
sudo -v
( while kill -0 $$ 2>/dev/null; do sudo -n true; sleep 50; done ) &
keepalive=$!

if [ "$reuse" = "yes" ]; then
    echo "== Reusing the finished image. Now choose your passphrase."
    build/kd usb --iso "$iso" --tier "$tier" --image "$image" --persistence-only
else
    echo "== Building the image. You will be asked to choose a passphrase in a few minutes."
    rm -f "$image"
    build/kd usb --iso "$iso" --tier "$tier" --image "$image" --size-gb "$size_gb" --library "$library"
fi
built="yes"

# The build takes a while, and a replugged disk can change numbers.
[ "$(fingerprint)" = "$identity" ] || fail "/dev/$device is no longer the drive you confirmed. Nothing was written to it."

echo "== Copying to /dev/$device"
# macOS services can briefly hold a stick. This drive is confirmed for erasing,
# so after a few polite tries it is safe to force.
unmounted="no"
for _ in 1 2 3 4 5; do
    if diskutil unmountDisk "/dev/$device" >/dev/null 2>&1; then unmounted="yes"; break; fi
    sleep 3
done
[ "$unmounted" = "yes" ] || diskutil unmountDisk force "/dev/$device"
sudo dd if="$image" of="/dev/r$device" bs=4m status=progress
sync
sleep 3

verify_stick

finished="yes"
rm -f "$image"
diskutil eject "/dev/$device"
echo "Done. Corrupted? Still alive. You can unplug the stick."
