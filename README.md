# Kill-Day OS

*Corrupted? Still alive.*

A bootable survival USB. It starts on almost any x86_64 PC with no internet and gives you a searchable offline library, offline maps, recovery tools and encrypted personal storage. All content is open-source, freely licensed or public domain, and every source is listed in `content/manifest.json`.

If the USB will not boot on a machine, plug it into any working Windows or Mac computer and run `START-WINDOWS` or `START-MAC` from the `KILLDAY_LIB` drive. The library runs from there.

## Size tiers

| Tier | USB size | Library content | General reference | Maps |
|---|---|---|---|---|
| Lite | 64 GB | about 35 GB | Wikipedia introductions | World, US lower 48 to street-name scale |
| Plus | 128 GB | about 80 GB | All of Wikipedia, text only, plus the offline AI model | World, US lower 48 to street-name scale |
| Standard | 256 GB | about 124 GB | All of Wikipedia, text only | Plus North America at street level |
| Full | 1 TB | about 520 GB | All of Wikipedia with images, Khan Academy | Plus the whole planet at street level |

Pick modules with `--modules`, and see each tier's exact list with `build/download-content.sh --tier lite --list`. Modules: general, medical, self-reliance, food, water, shelter, comms, education, maps, ai.

## USB layout

| # | Label | Format | Holds |
|---|---|---|---|
| 1 | `KILLDAYBOOT` | FAT32 | GRUB for UEFI and BIOS, kernel |
| 2 | none (squashfs) | read-only squashfs | The operating system |
| 3 | `KILLDAY_PERSIST` | LUKS2 + ext4 | Your encrypted home folder and Wi-Fi networks |
| 4 | `KILLDAY_LIB` | exFAT | The library, readable on Windows and macOS |

The labels `KILLDAY_BOOT` and `KILLDAY_LIBRARY` were shortened because FAT32 and exFAT labels hold at most 11 characters.

## Hardware

- x86_64 PC, UEFI or legacy BIOS. 4 GB RAM minimum, 8 GB recommended.
- Boots with Secure Boot on through Debian's Microsoft-signed boot chain. This is tested in emulation, including passphrase entry, but not yet on real hardware (see RUNBOOK section 6). The memory test needs Secure Boot off.
- Includes firmware for common Intel, Realtek, Atheros, Broadcom and AMD hardware.
- Apple Silicon and ARM machines cannot boot it, but can use the library partition.

## Base system

Debian 13 "trixie", built with live-build, which keeps the partition layout under direct control and uses Debian's own signed boot chain. Ventoy would add a third-party boot layer that wants to own the disk layout, which conflicts with the four-partition design.

## Start here

See [RUNBOOK.md](RUNBOOK.md) to build and write a USB, and [docs/LIMITATIONS.md](docs/LIMITATIONS.md) for what it does not do. Print `docs/killday-if-youre-stuck.pdf` and `branding/label/killday-usb-label.pdf` to keep with the drive.

## Safety

Everything here is reference material and is not a substitute for professional care. Medical, chemical, electrical and food pages carry a visible warning in the Almanac. Sources that teach building weapons or explosives are excluded (see the `excluded` list in `content/sources.json`). The optional AI assistant is unreliable and must not be used for medical or safety-critical decisions.

## License

The code, portal and branding in this repository are under the [MIT License](LICENSE). Bundled fonts keep the SIL Open Font License (see `branding/fonts`). Library content is not in this repository. It is downloaded at build time, and each item keeps its own license, listed in `content/manifest.json` and on the Almanac's About page. Some items are non-commercial, so copies may be given away but not sold.
