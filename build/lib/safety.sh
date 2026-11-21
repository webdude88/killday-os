#!/usr/bin/env bash
# Guards that stand between the USB writer and the wrong disk. Kept separate so
# build/test-safety.sh can exercise every refusal with mocked disks.

# Wrappers around system queries, overridden by the tests. Mount tables come from
# PID 1 so the checks still see the host when run in a --pid=host container.
kd_all_mounts() { findmnt --task 1 -rno SOURCE,TARGET; }
kd_system_mount_source() { findmnt --task 1 -no SOURCE "$1" 2>/dev/null || true; }
kd_swap_sources() { swapon --noheadings --show=NAME 2>/dev/null || true; }
kd_children_of() { lsblk -nrpo NAME "$1" 2>/dev/null; }
kd_disk_field() { lsblk -dno "$2" "$1" 2>/dev/null | sed 's/^ *//;s/ *$//'; }

# Prints every whole disk under a device, through LUKS, LVM and RAID layers.
kd_root_disks() { lsblk -nsrpo NAME,TYPE "$1" 2>/dev/null | awk '$2 == "disk" {print $1}'; }

# Prints every disk the running system depends on.
kd_system_disks() {
    local point source
    for point in / /boot /boot/efi /usr /var /home /run/live/medium /run/live/persistence; do
        source=$(kd_system_mount_source "$point")
        source="${source%%\[*}"  # btrfs reports /dev/sda2[/@]
        case "$source" in /dev/*) kd_root_disks "$source" ;; esac
    done
    while IFS= read -r source; do
        case "$source" in /dev/*) kd_root_disks "$source" ;; esac
    done < <(kd_swap_sources)
}

# Prints mountpoints of anything on the device or its partitions.
kd_mounted_under() {
    local children
    children=$(kd_children_of "$1")
    kd_all_mounts | awk -v list="$children" '
        BEGIN { n = split(list, names, "\n"); for (i = 1; i <= n; i++) wanted[names[i]] = 1 }
        ($1 in wanted) { print $2 }'
}

# Refuses partitions, non-block paths, the system disk and busy disks.
kd_validate_target() {
    local device="$1" type
    case "$device" in
        /dev/*) ;;
        *) echo "REFUSED: '$device' is not a /dev path." >&2; return 1 ;;
    esac
    if [ ! -b "$device" ] && [ -z "${KD_SAFETY_TEST:-}" ]; then
        echo "REFUSED: $device is not a block device." >&2
        return 1
    fi
    type=$(kd_disk_field "$device" TYPE)
    if [ "$type" != "disk" ]; then
        echo "REFUSED: $device is a '$type', not a whole disk. Give the disk, such as /dev/sdb." >&2
        return 1
    fi
    # Captured first: "cmd | grep -q" under pipefail reports failure when grep
    # exits early, which would let the system disk through.
    local system_disks
    system_disks=$(kd_system_disks | sort -u)
    if [ -z "$system_disks" ]; then
        echo "REFUSED: could not identify the system disk, so no disk can be proven safe." >&2
        echo "In Docker, use 'build/kd usb', which passes --pid=host." >&2
        return 1
    fi
    if grep -qxF "$device" <<<"$system_disks"; then
        echo "REFUSED: $device holds the running system." >&2
        return 1
    fi
    local mounted
    mounted=$(kd_mounted_under "$device")
    if [ -n "$mounted" ]; then
        echo "REFUSED: $device has mounted filesystems. Unmount them first:" >&2
        echo "$mounted" >&2
        return 1
    fi
}

# Non-USB disks are treated as internal and need a second, harder confirmation.
kd_is_usb() { [ "$(kd_disk_field "$1" TRAN)" = "usb" ]; }

kd_confirm_target() {
    local device="$1" allow_internal="$2" answer
    echo
    echo "ALL DATA ON THIS DISK WILL BE PERMANENTLY ERASED:"
    echo "  Device : $device"
    echo "  Model  : $(kd_disk_field "$device" VENDOR) $(kd_disk_field "$device" MODEL)"
    echo "  Size   : $(kd_disk_field "$device" SIZE)"
    echo "  Bus    : $(kd_disk_field "$device" TRAN)"
    echo
    if ! kd_is_usb "$device"; then
        if [ "$allow_internal" != "yes" ]; then
            echo "REFUSED: $device is not connected by USB, so it may be an internal disk." >&2
            echo "Re-run with --allow-non-usb only if you are certain." >&2
            return 1
        fi
        echo "WARNING: this disk is NOT on USB. It may be an internal disk."
        read -r -p "Type ERASE-INTERNAL-DISK to continue: " answer
        [ "$answer" = "ERASE-INTERNAL-DISK" ] || { echo "Cancelled." >&2; return 1; }
    fi
    read -r -p "Type the device name exactly ($device) to erase it: " answer
    [ "$answer" = "$device" ] || { echo "Cancelled. Nothing was changed." >&2; return 1; }
}
