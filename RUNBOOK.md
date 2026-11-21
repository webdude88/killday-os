# Kill-Day OS runbook

Commands run from the project root. All builds run in Docker, so the only host requirement is Docker with `--privileged` support.

**Writing to a real USB needs Linux or a Mac.** Docker Desktop cannot pass USB drives into containers, so Macs use `build/usb-from-mac.sh` (section 3), and Windows is not supported for this step. Building the ISO and downloading content work on a Mac.

## 1. Build

```sh
build/kd images                                   # Build the two tool containers (first time only)
KD_TIER=lite build/kd builder build/build-iso.sh  # Tier: lite, plus, standard or full
```

The result is `out/killday-os-<version>-<tier>.iso`. It boots by itself for testing, but persistence and the library need the USB layout below.

## 2. Download the library

```sh
build/kd builder python3 content/tools/download.py --tier lite --list      # See what you will get
build/kd builder python3 content/tools/download.py --tier lite             # Everything for the tier
build/kd builder python3 content/tools/download.py --tier standard --modules medical,water,maps
build/kd builder python3 content/tools/download.py --tier standard --with-optional   # Adds the AI model
KD_TIER=lite build/kd builder build/build-library.sh                       # Portal, search index, launchers
```

Interrupted downloads resume when you re-run the command, and every file is checksum-verified. To add a map region, add a `region(...)` line in `content/tools/write_sources.py` and re-run the steps in section 7.

## 3. Write to USB (Linux)

Find the stick's name with `lsblk -o NAME,MODEL,SIZE,TRAN`. Then:

```sh
sudo KD_TIER=lite build/kd usb --iso out/killday-os-1.0.0-lite.iso --tier lite --device /dev/sdX
```

You will see the model and size and must type the device name to continue. It refuses the system disk, disks with mounted filesystems, partitions, and anything not on USB. `--allow-non-usb` exists for USB-to-SATA oddities and needs a second typed confirmation.

Run it through `build/kd usb`, which passes `--pid=host` so the guards can see your real disks. Without that it refuses to write.

**On a Mac**, find the stick with `diskutil list external physical`, then run this from a terminal:

```sh
build/usb-from-mac.sh --device diskN --tier lite
```

It builds the real layout as an image file in `out/`, copies that to the stick, checks the result and deletes the image. You need free space for the image on the drive holding the project, about the size of the stick. It shows the model and size and makes you type the device name, and refuses anything internal, fixed, not USB, or holding the system or this project.

For the 128 GB Plus tier, point it at the Plus library:

```sh
build/usb-from-mac.sh --device diskN --tier plus --library out/library-plus
```

**Preparing an image ahead of time.** The build takes a while and the copy needs your Mac password, so the image can be built first and copied later. Build it with a throwaway passphrase file and the stick's size in GiB (bytes divided by 1073741824, rounded down), then delete the passphrase file:

```sh
docker run --rm --platform linux/amd64 --privileged --pid=host -v /dev:/dev -v "$PWD:/work" -w /work killday-builder \
    build/write-usb.sh --iso out/killday-os-1.0.0-plus.iso --tier plus --image out/killday-usb-plus.img \
    --size-gb 115 --passphrase-file out/.prebuild-pass --library out/library-plus
```

Then add `--reuse-image` to the `usb-from-mac.sh` command. It re-creates the encrypted partition with a fresh key and the passphrase you choose, so nothing from the throwaway passphrase survives, and then copies.

If the check after the copy is cut short (for example the stick drops off a hub), replug it and run the same command with `--verify-only` instead of `--reuse-image`. It writes nothing, compares the stick with the image, audits the library, and then deletes the image.

## 4. First boot and your passphrase

1. Boot from the USB (usually F12, F9, F10, F8 or Esc at power-on) and choose **Normal**.
2. Enter the passphrase you set when writing the USB. A forgotten passphrase cannot be recovered, and nobody can reset it.
3. The Almanac opens by itself after login. Login is automatic as user `survivor`.

To change the passphrase, boot Kill-Day OS and run `sudo cryptsetup luksChangeKey /dev/sdX3`, using the USB's name from `lsblk`.

## 5. Boot menu

| Entry | Use |
|---|---|
| Normal | Everyday use. Asks for the passphrase and shows the splash. |
| Safe graphics | Blank or garbled screen. |
| Persistence on | Same as Normal with boot text visible, for troubleshooting. |
| Persistence off | Saves nothing and asks for no passphrase. |
| Load to RAM | Lets you remove the USB. Needs 8 GB or more. |
| Memory test | Tests RAM. Turn Secure Boot off first. |

## 6. Secure Boot

Kill-Day OS boots with Secure Boot on: Microsoft-signed shim, then Debian-signed GRUB, then the Debian-signed kernel.

**Test status:** under emulated Secure Boot with Microsoft's keys, the boot chain, passphrase entry, desktop, library, search and maps all work. It has not yet been tried on real hardware, so try it once on your own machine before you depend on it.

If the passphrase prompt does not respond with Secure Boot on, either choose **Persistence off** (the library still works, but nothing is saved), or disable Secure Boot in firmware setup.

Also note:

- Memory test is unsigned, so it fails under Secure Boot.
- Firmware that only trusts Windows' certificate (the "Microsoft 3rd-party UEFI CA" option off) will reject the USB. Turn on third-party certificates or disable Secure Boot in firmware setup.

## 7. Updating

With internet, on a Linux machine, mount the library read-write and run:

```sh
sudo mount /dev/sdX4 /mnt/kd
KD_TIER=lite build/kd builder build/update-content.sh --library /mnt/kd --tier lite
```

Because `build/kd` only sees the project folder, either mount the library under the project (for example `out/mnt`) or run the script on the host with the tools installed. It re-verifies every source, downloads newer files, and removes old ones only after the new set verifies.

Under a running Kill-Day OS the library is read-only. Use `sudo mount -o remount,rw /srv/library` only when you mean to change it, and remount read-only afterwards.

**OS updates:** build a new ISO and re-run section 3 on a blank stick. The ISO version is what you are upgrading.

## 7a. Highlighting your home county

The map can outline one US county and open on it, with a button to jump back. Find the county's 5-digit FIPS code (state code plus county code; Waseca County, Minnesota is 27161), then:

```sh
python3 content/tools/make_home_area.py 27161
KD_TIER=plus build/kd builder build/build-library.sh
```

The boundary comes from the US Census Bureau and is public domain. The file it writes, `portal/src/data/home-area.geojson`, is kept out of git. To update a stick that is already written, copy `map.html`, `about.html` and the `data` folder from `out/library-<tier>/almanac/` into `almanac/` on the `KILLDAY_LIB` drive.

## 8. Checking a library

```sh
build/audit-library.sh /path/to/library
```

It reports missing and corrupted files, and exits with status 1 if anything is wrong.

## 9. Copying for family

Write a fresh USB for each person with section 3 so everyone has their own passphrase and encryption key. Then copy the library:

```sh
rsync -rt --inplace --modify-window=2 --info=progress2 /mnt/source-lib/ /mnt/new-lib/
```

Avoid `dd` cloning a whole stick. A clone shares the same LUKS master key, so one leaked key compromises every copy, even if you later change the passphrase on one of them.

Some content is licensed non-commercially. Giving copies away is fine. Selling them is not.

## 10. Tests

```sh
build/kd builder build/test-safety.sh     # USB writer refusal tests, touches no disks
build/kd builder build/lint.sh            # shellcheck
KD_STAGING=/work/out/test-library KD_TIER=lite build/kd builder build/make-test-image.sh
build/kd tester build/smoke-test.sh uefi bios secureboot
```

Screenshots and serial logs land in `out/test-results/`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| USB is not in the boot menu | Try another port (USB 2.0 ports are most compatible). Enable "Legacy/CSM" or USB boot in firmware setup. |
| Passphrase is rejected | Press Y to retry. Check Caps Lock. The keyboard layout at this stage is US. |
| Blank screen after the menu | Choose Safe graphics. |
| Library tiles all look faded | The `KILLDAY_LIB` partition did not mount. Check it with `lsblk -f`. |
| Windows does not show the drive | It needs Windows 10 version 1703 or later for multi-partition USB drives. |
| "Windows protected your PC" | Choose More info, then Run anyway. The launcher is unsigned. |
