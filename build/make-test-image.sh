#!/usr/bin/env bash
# Builds a throwaway USB image for the smoke tests, using the real writer and a
# small real library. The passphrase here protects nothing: the image is deleted.
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck source=build/config.sh
source build/config.sh

TIER="${KD_TIER:-lite}"
iso="$KD_OUT/killday-os-$KD_VERSION-$TIER.iso"
test_dir=/build/test
mkdir -p "$test_dir"
rm -f "$test_dir/killday-test.img"
printf 'zombie-test-phrase' > "$test_dir/passphrase"

build/write-usb.sh --iso "$iso" --tier "$TIER" --image "$test_dir/killday-test.img" --size-gb 16 \
    --passphrase-file "$test_dir/passphrase" --library "$KD_STAGING" --test-layout

# Only the test copy gets the probe flag and a short menu timeout.
cfg="$test_dir/grub.cfg"
mcopy -n -i "$test_dir/killday-test.img@@1M" ::/boot/grub/grub.cfg "$cfg"
sed -i 's|^set timeout=10|set timeout=2|; s|^set live="|set live="killday.test |' "$cfg"
mcopy -o -i "$test_dir/killday-test.img@@1M" "$cfg" ::/boot/grub/grub.cfg
ls -lh "$test_dir/killday-test.img"
