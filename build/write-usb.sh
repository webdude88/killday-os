#!/usr/bin/env bash
# Lays out a Kill-Day USB:
#   1 FAT32 boot   2 read-only squashfs live system
#   3 LUKS2 ext4 persistence   4 exFAT library
# Usage: write-usb.sh --iso FILE --tier TIER --device /dev/sdX [--allow-non-usb]
#        write-usb.sh --iso FILE --tier TIER --image FILE --size-gb N [--passphrase-file FILE] [--test-layout]
#        write-usb.sh --iso FILE --tier TIER --image FILE --persistence-only [--passphrase-file FILE]
# --persistence-only re-creates just the encrypted partition of a finished image,
# so a prepared image can get its owner's passphrase without a full rebuild.
set -euo pipefail
script_dir="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=build/config.sh
source "$script_dir/config.sh"
# shellcheck source=build/lib/safety.sh
source "$script_dir/lib/safety.sh"

iso="" tier="" device="" image="" size_gb="" pass_file="" allow_internal="no" library="$KD_STAGING" test_layout="no" persist_only="no"
while [ $# -gt 0 ]; do
    case "$1" in
        --iso) iso="$2"; shift 2 ;;
        --tier) tier="$2"; shift 2 ;;
        --device) device="$2"; shift 2 ;;
        --image) image="$2"; shift 2 ;;
        --size-gb) size_gb="$2"; shift 2 ;;
        --passphrase-file) pass_file="$2"; shift 2 ;;
        --allow-non-usb) allow_internal="yes"; shift ;;
        --test-layout) test_layout="yes"; shift ;;
        --persistence-only) persist_only="yes"; shift ;;
        --library) library="$2"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
done

[ "$(id -u)" -eq 0 ] || { echo "Run as root." >&2; exit 1; }
validate_tier "$tier"
[ -f "$iso" ] || { echo "ISO not found: $iso" >&2; exit 1; }
if [ -n "$device" ] && [ -n "$image" ]; then echo "Choose --device or --image, not both." >&2; exit 2; fi
if [ -z "$device" ] && [ -z "$image" ]; then echo "--device is required." >&2; exit 2; fi
# A passphrase on disk is only acceptable for throwaway test images.
if [ -n "$device" ] && [ -n "$pass_file" ]; then echo "--passphrase-file is only allowed with --image." >&2; exit 2; fi
if [ "$persist_only" = "yes" ] && { [ -z "$image" ] || [ ! -f "$image" ]; }; then echo "--persistence-only needs an existing --image." >&2; exit 2; fi

work=$(mktemp -d)
loop="" mapper="killday-write-$$"
cleanup() {
    set +e
    for mountpoint in "$work/boot" "$work/persist" "$work/library"; do
        mountpoint -q "$mountpoint" && umount "$mountpoint"
    done
    [ -e "/dev/mapper/$mapper" ] && cryptsetup close "$mapper"
    # Linux keeps partitions added to a loop device after it detaches, and they
    # would break the next image, so remove them first.
    [ -n "$loop" ] && { partx -d "$loop" 2>/dev/null; losetup -d "$loop"; }
    rm -rf "$work"
}
trap cleanup EXIT

if [ -n "$image" ]; then
    [ "$persist_only" = "yes" ] || truncate -s "${size_gb:?--size-gb is required with --image}G" "$image"
    loop=$(losetup -f --show "$image")
    partx -d "$loop" 2>/dev/null || true
    target="$loop"
else
    kd_validate_target "$device"
    kd_confirm_target "$device" "$allow_internal"
    target="$device"
    size_bytes=$(blockdev --getsize64 "$target")
    min_gb=$(tier_setting "$tier" min_gb)
    if [ "$size_bytes" -lt $((min_gb * 1000000000)) ]; then
        echo "The $tier tier needs at least $min_gb GB, and this disk is smaller." >&2
        exit 1
    fi
fi

boot_mb=$(tier_setting "$tier" boot)
live_mb=$(tier_setting "$tier" live)
persist_mb=$(tier_setting "$tier" persist)
if [ "$test_layout" = "yes" ]; then live_mb=6144; persist_mb=512; fi

live_start=$((1 + boot_mb))
persist_start=$((live_start + live_mb))
library_start=$((persist_start + persist_mb))
# An MBR table cannot address past 2 TiB, so anything beyond that stays unused.
total_mb=$(( $(blockdev --getsize64 "$target") / 1048576 ))
end_mb=$(( total_mb > 2097151 ? 2097151 : total_mb - 1 ))

if [ "$persist_only" = "no" ]; then
echo "== Partitioning (MBR, for the widest BIOS and UEFI compatibility)"
wipefs -a "$target" >/dev/null
parted -s -a optimal "$target" \
    mklabel msdos \
    mkpart primary fat32 1MiB "${live_start}MiB" \
    mkpart primary ext4 "${live_start}MiB" "${persist_start}MiB" \
    mkpart primary ext4 "${persist_start}MiB" "${library_start}MiB" \
    mkpart primary ntfs "${library_start}MiB" "${end_mb}MiB" \
    set 1 boot on set 1 esp on
fi
partprobe "$target" 2>/dev/null || true
udevadm settle 2>/dev/null || true

part_name() {
    case "$target" in
        *[0-9]) echo "${target}p$1" ;;
        *) echo "${target}$1" ;;
    esac
}
# Containers snapshot /dev at start, so new partition nodes may need creating.
# A node left by an earlier run can point at the wrong partition, so it is only
# trusted when its numbers match what the kernel reports.
ensure_node() {
    local node="$1" sys want
    sys="/sys/class/block/$(basename "$node")/dev"
    for _ in $(seq 1 20); do
        if [ -r "$sys" ]; then
            want=$(cat "$sys")
            [ -b "$node" ] && [ "$(printf '%d:%d' "0x$(stat -c %t "$node")" "0x$(stat -c %T "$node")")" = "$want" ] && return 0
            rm -f "$node"
            mknod "$node" b "${want%%:*}" "${want##*:}"
            return 0
        fi
        sleep 0.5
    done
    echo "Partition $node never appeared." >&2
    exit 1
}
for number in 1 2 3 4; do ensure_node "$(part_name "$number")"; done

p_boot=$(part_name 1) p_live=$(part_name 2) p_persist=$(part_name 3) p_library=$(part_name 4)

create_persistence() {
    echo "== Creating encrypted persistence"
    # A fresh header and volume key every time, so nothing from an earlier format survives.
    dd if=/dev/zero of="$p_persist" bs=1M count=32 conv=fsync status=none
    # Fixed KDF cost, so a stick formatted on a fast PC still unlocks on an old one.
    luks_args=(--type luks2 --cipher aes-xts-plain64 --key-size 512 --hash sha256 --pbkdf argon2id
               --pbkdf-force-iterations 4 --pbkdf-memory 262144 --pbkdf-parallel 2 --label "$KD_LABEL_PERSIST")
    if [ -n "$pass_file" ]; then
        cryptsetup luksFormat --batch-mode "${luks_args[@]}" --key-file "$pass_file" "$p_persist"
        cryptsetup open --key-file "$pass_file" "$p_persist" "$mapper"
    else
        echo "Choose a passphrase for your encrypted storage. If you forget it, the data is gone."
        cryptsetup luksFormat --batch-mode --verify-passphrase "${luks_args[@]}" "$p_persist"
        echo "Enter the passphrase once more to finish setup."
        cryptsetup open "$p_persist" "$mapper"
    fi
    [ -b "/dev/mapper/$mapper" ] || udevadm settle 2>/dev/null || true
    mkfs.ext4 -q -L "$KD_LABEL_PERSIST" "/dev/mapper/$mapper"
    mkdir -p "$work/persist"
    mount "/dev/mapper/$mapper" "$work/persist"
    printf '/home union\n/etc/NetworkManager/system-connections union\n' > "$work/persist/persistence.conf"
    sync
    umount "$work/persist"
    cryptsetup close "$mapper"
}

if [ "$persist_only" = "yes" ]; then
    create_persistence
    sync
    echo "Encrypted storage re-created."
    exit 0
fi

echo "== Extracting the ISO"
mkdir -p "$work/iso" "$work/wrap/live"
xorriso -osirrox on -indev "$iso" -extract /live "$work/iso/live" -extract /boot/grub/killday "$work/iso/theme" >/dev/null 2>&1
chmod -R u+w "$work/iso"

echo "== Writing boot partition"
mkfs.vfat -F 32 -n "$KD_LABEL_BOOT" "$p_boot" >/dev/null
mkdir -p "$work/boot"
mount "$p_boot" "$work/boot"
mkdir -p "$work/boot/live" "$work/boot/.disk" "$work/boot/boot/grub/killday" "$work/boot/EFI/BOOT" "$work/boot/EFI/debian"
cp "$work/iso/live/vmlinuz" "$work/iso/live/initrd.img" "$work/iso/live/memtest86+x64.bin" "$work/iso/live/memtest86+x64.efi" "$work/boot/live/"
cp -R "$work/iso/theme/." "$work/boot/boot/grub/killday/"
cp "$KD_ROOT/branding/grub/grub.cfg" "$work/boot/boot/grub/grub.cfg"
touch "$work/boot/.disk/killday-boot"
# Debian's signed chain keeps Secure Boot working: shim, then signed GRUB.
cp /usr/lib/shim/shimx64.efi.signed "$work/boot/EFI/BOOT/BOOTX64.EFI"
cp /usr/lib/shim/mmx64.efi.signed "$work/boot/EFI/BOOT/mmx64.efi"
cp /usr/lib/grub/x86_64-efi-signed/grubx64.efi.signed "$work/boot/EFI/BOOT/grubx64.efi"
# shellcheck disable=SC2016  # $root and $prefix are GRUB variables.
stub='search --no-floppy --set=root --file /.disk/killday-boot
set prefix=($root)/boot/grub
configfile $prefix/grub.cfg'
echo "$stub" > "$work/boot/EFI/debian/grub.cfg"
echo "$stub" > "$work/boot/EFI/BOOT/grub.cfg"
grub-install --target=i386-pc --boot-directory="$work/boot/boot" --modules="part_msdos fat" --force "$target" 2>&1 | tail -1
sync
umount "$work/boot"

echo "== Writing read-only live system"
mv "$work/iso/live/filesystem.squashfs" "$work/wrap/live/"
# Uncompressed wrapper: the inner image is already compressed, and live-boot
# finds it on this partition exactly as it would on an ISO.
mksquashfs "$work/wrap" "$work/live.img" -noI -noD -noF -noX -no-xattrs -all-root -noappend -quiet -no-progress
image_mb=$(( $(stat -c %s "$work/live.img") / 1048576 ))
[ "$image_mb" -lt "$live_mb" ] || { echo "Live system (${image_mb} MiB) does not fit in ${live_mb} MiB." >&2; exit 1; }
dd if="$work/live.img" of="$p_live" bs=4M conv=fsync status=none

create_persistence

echo "== Writing library"
mkfs.exfat -L "$KD_LABEL_LIBRARY" "$p_library" >/dev/null
parted -s "$target" type 4 0x07 2>/dev/null || sfdisk --part-type "$target" 4 07 >/dev/null 2>&1 || true
ensure_node "$p_library"
if [ -d "$library/almanac" ]; then
    mkdir -p "$work/library"
    mount -t exfat "$p_library" "$work/library"
    rsync -rt --inplace --modify-window=2 --exclude '*.part' --info=progress2 "$library/" "$work/library/"
    sync
    umount "$work/library"
else
    echo "No staged library at $library. Partition 4 is empty; run build-library.sh and copy it later."
fi

sync
echo "Done. Corrupted? Still alive."
