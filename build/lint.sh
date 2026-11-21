#!/usr/bin/env bash
# Runs shellcheck over every shell script in the project.
set -euo pipefail
cd "$(dirname "$0")/.."
mapfile -t scripts < <(
    { find build docs portal content branding -type f -name '*.sh'
      find build/live-build/includes.chroot/usr/lib/killday build/live-build/includes.chroot/usr/local/bin -type f
      find build/live-build/hooks -type f
      echo build/kd
      echo build/live-build/includes.chroot/etc/initramfs-tools/hooks/killday-crypt
    } | sort -u)
files=()
for script in "${scripts[@]}"; do
    head -1 "$script" | grep -q '^#!.*sh' && files+=("$script")
done
shellcheck -x "${files[@]}"
echo "shellcheck clean: ${#files[@]} scripts"
