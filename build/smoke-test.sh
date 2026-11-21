#!/usr/bin/env bash
# Boots the test image in QEMU and checks boot, persistence, portal, search and
# map. Usage: build/kd tester build/smoke-test.sh [bios|uefi|secureboot ...]
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 build/tests/smoke.py "${@:-uefi bios}"
