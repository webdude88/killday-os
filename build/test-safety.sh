#!/usr/bin/env bash
# Proves every USB-writer refusal using mocked disks. Touches no real device.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
# shellcheck source=build/lib/safety.sh
source build/lib/safety.sh
export KD_SAFETY_TEST=1

passed=0 failed=0
expect() { # expect <0|1> <description> <command...>
    local want="$1" name="$2"; shift 2
    "$@" >/dev/null 2>&1 </dev/null
    local got=$?
    if { [ "$want" -eq 0 ] && [ "$got" -eq 0 ]; } || { [ "$want" -ne 0 ] && [ "$got" -ne 0 ]; }; then
        passed=$((passed + 1)); echo "ok   - $name"
    else
        failed=$((failed + 1)); echo "FAIL - $name (exit $got)"
    fi
}

# The mock machine: root is on LVM spanning sda and sdd, sdb is a free USB
# stick, sdc is a busy USB stick, nvme0n1 is a free internal disk.
kd_system_mount_source() {
    case "$1" in
        /) echo "${MOCK_ROOT-/dev/mapper/vg-root}" ;;
        /boot) echo "${MOCK_BOOT-/dev/sda2}" ;;
        *) echo "" ;;
    esac
}
kd_swap_sources() { [ -n "${MOCK_ROOT-x}" ] && echo /dev/mapper/vg-swap; return 0; }
kd_root_disks() {
    case "$1" in
        /dev/mapper/vg-root|/dev/mapper/vg-swap) printf '/dev/sda\n/dev/sdd\n' ;;
        /dev/sda2) echo /dev/sda ;;
        /dev/sde1) echo /dev/sde ;;
    esac
}
kd_children_of() { printf '%s\n%s1\n' "$1" "$1"; }
kd_all_mounts() { echo "/dev/sdc1 /media/stick"; }
kd_disk_field() {
    case "$1:$2" in
        /dev/sdb1:TYPE) echo part ;;
        *:TYPE) echo disk ;;
        /dev/sdb:TRAN|/dev/sdc:TRAN) echo usb ;;
        /dev/sda:TRAN|/dev/nvme0n1:TRAN) echo sata ;;
        *:SIZE) echo 64G ;;
        *) echo X ;;
    esac
}

confirm_with() { local input="$1"; shift; kd_confirm_target "$@" <<<"$input"; }

expect 1 "refuses a non-/dev path"             kd_validate_target /tmp/disk.img
expect 1 "refuses the disk under an LVM root"  kd_validate_target /dev/sda
expect 1 "refuses every disk of a multi-disk root" kd_validate_target /dev/sdd
expect 1 "refuses a partition"                 kd_validate_target /dev/sdb1
expect 1 "refuses a disk with mounts"          kd_validate_target /dev/sdc
expect 0 "accepts a free USB stick"            kd_validate_target /dev/sdb
expect 0 "accepts the exact typed name"        confirm_with /dev/sdb /dev/sdb no
expect 1 "rejects a wrong typed name"          confirm_with /dev/sdc /dev/sdb no
expect 1 "rejects an empty answer"             confirm_with "" /dev/sdb no
expect 1 "rejects 'yes' as confirmation"       confirm_with yes /dev/sdb no
expect 1 "refuses internal disk without flag"  confirm_with /dev/nvme0n1 /dev/nvme0n1 no
expect 1 "flag alone does not skip the phrase" confirm_with /dev/nvme0n1 /dev/nvme0n1 yes
expect 0 "internal needs phrase and name"      confirm_with $'ERASE-INTERNAL-DISK\n/dev/nvme0n1' /dev/nvme0n1 yes

# Many system disks force grep to exit before the writer finishes (SIGPIPE case).
noisy_disks() { for i in $(seq 1 20000); do echo "/dev/zz$i"; done; echo /dev/sda; for i in $(seq 1 20000); do echo "/dev/yy$i"; done; }
with_noise() { kd_system_disks() { noisy_disks; }; kd_validate_target /dev/sda; }
# shellcheck disable=SC2317  # Invoked indirectly through expect.
blind() { export MOCK_ROOT="overlay" MOCK_BOOT=""; kd_swap_sources() { :; }; kd_validate_target /dev/sdb; }
# shellcheck disable=SC2317  # Invoked indirectly through expect.
subvol() { export MOCK_ROOT="/dev/sde1[/@]" MOCK_BOOT=""; kd_swap_sources() { :; }; kd_validate_target /dev/sde; }
expect 1 "still refuses with a long disk list" bash -c "set -o pipefail; source build/lib/safety.sh; export KD_SAFETY_TEST=1; $(declare -f kd_disk_field kd_mounted_under noisy_disks with_noise); with_noise"
expect 1 "fails closed when the host is invisible" blind
expect 1 "sees through btrfs subvolume names" subvol

echo "$passed passed, $failed failed"
[ "$failed" -eq 0 ]
