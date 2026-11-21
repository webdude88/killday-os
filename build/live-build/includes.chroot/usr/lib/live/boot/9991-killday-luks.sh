#!/bin/sh
# Overrides live-boot's check so the passphrase prompt only appears for the
# Kill-Day partition. Stock live-boot would prompt for any LUKS disk in the
# host, including a borrowed laptop's encrypted internal drive.
is_luks_partition ()
{
	device="${1}"
	[ "$(blkid -s LABEL -o value "${device}" 2>/dev/null)" = "KILLDAY_PERSIST" ] || return 1
	/sbin/cryptsetup isLuks "${device}" >/dev/null 2>&1
}
