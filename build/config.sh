#!/usr/bin/env bash
# Shared settings for every Kill-Day OS build script. Source this file.
# shellcheck disable=SC2034  # Variables are consumed by the scripts that source this.

KD_VERSION="${KD_VERSION:-1.0.0}"
KD_DISTRIBUTION="trixie"
KD_USERNAME="survivor"
KD_HOSTNAME="killday"
KD_PORT=8642
KD_KIWIX_PORT=8643

# FAT32 and exFAT volume labels are capped at 11 characters, so the requested
# KILLDAY_BOOT and KILLDAY_LIBRARY cannot be stored literally.
KD_LABEL_BOOT="KILLDAYBOOT"
KD_LABEL_PERSIST="KILLDAY_PERSIST"
KD_LABEL_LIBRARY="KILLDAY_LIB"

KD_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KD_OUT="${KD_OUT:-$KD_ROOT/out}"
KD_STAGING="${KD_STAGING:-$KD_ROOT/out/library}"

# tier_setting TIER FIELD -> boot|live|persist size in MiB, or minimum disk GB.
tier_setting() {
    local tier="$1" field="$2"
    case "$tier:$field" in
        lite:boot|plus:boot|standard:boot|full:boot)  echo 1024 ;;
        lite:live|plus:live|standard:live|full:live)  echo 12288 ;;
        lite:persist)                          echo 8192 ;;
        plus:persist)                          echo 16384 ;;
        standard:persist)                      echo 32768 ;;
        full:persist)                          echo 65536 ;;
        lite:min_gb)                           echo 56 ;;
        plus:min_gb)                           echo 120 ;;
        standard:min_gb)                       echo 220 ;;
        full:min_gb)                           echo 880 ;;
        *) echo "unknown tier setting: $tier:$field" >&2; return 1 ;;
    esac
}

validate_tier() {
    case "${1:-}" in
        lite|plus|standard|full) ;;
        *) echo "Tier must be lite, plus, standard or full (got '${1:-}')." >&2; return 1 ;;
    esac
}
