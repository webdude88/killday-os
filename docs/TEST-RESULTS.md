# Test results

## Plus tier, 2026-11-20

Run against `killday-os-1.0.0-plus.iso` (kernel 6.12.117, 29 package updates over Lite), written by the real `build/write-usb.sh` to a 16 GB loop-device image with the same small test library as below. x86_64 guests ran under QEMU software emulation.

| Check | UEFI | BIOS | Secure Boot |
|---|---|---|---|
| Boots to desktop, Almanac opens | Pass | Pass | Pass |
| Passphrase unlocks persistence | Pass | Pass | Pass |
| Wrong passphrase can be retried | Pass | Pass | Pass |
| Files survive a reboot | Pass | Pass | Pass |
| Library, Kiwix search, safety banners, combined search, map | Pass | Pass | Pass |

All 45 checks pass, so passphrase entry under Secure Boot is now confirmed in emulation. The earlier "not confirmed" result came from the test harness: it typed once as soon as the prompt was drawn, and under emulation the prompt can be drawn before it reads keys. The harness now clears the field and retypes if the prompt is still up after 90 seconds, and it waits for the "Retry?" question instead of a fixed delay. A wrong-passphrase check only passes after a retry is actually answered.

Other Plus checks:

| Check | Result |
|---|---|
| Plus library audit | 56 of 56 files verify (75.2 GiB) |
| Full 115 GiB USB image, built from the real library | Library audit 56 of 56 inside the image, boot files and live system present |
| Re-creating encrypted storage on a finished image | Old passphrase rejected, new one unlocks, boot, live and library partitions byte-identical |
| AI assistant (`killday-ai`) | Answers and exits on `/exit`, run in the builder container with the real library. Not run inside the live system. |
| USB writer refusal tests | 16 of 16 pass |
| shellcheck | Clean, 29 scripts |

Bugs found and fixed in this round: `killday-ai` passed a flag the bundled llama.cpp no longer accepts, so it could never start, and the writer left loop-device partitions behind, which broke the next image build.

## Lite tier, 2026-11-09

Run on 2026-11-09 against `killday-os-1.0.0-lite.iso`, written by the real `build/write-usb.sh` to a 16 GB loop-device image. x86_64 guests ran under QEMU software emulation, with a small real library (2 ZIMs, 5 documents, 1 book, 1 map region). Screenshots and serial logs are in `out/test-results/`.

| Check | ISO | UEFI | BIOS | Secure Boot |
|---|---|---|---|---|
| Themed GRUB menu | Pass | Not captured | Not captured | Not captured |
| Boots to desktop | Pass | Pass | Pass | Pass |
| Almanac opens at login | Pass | Pass | Pass | Pass |
| Passphrase unlocks persistence | n/a | Pass | Pass | **Not confirmed** |
| Wrong passphrase can be retried | n/a | Pass | Pass | Not confirmed |
| Files survive a reboot | n/a | Pass | Pass | Not confirmed |
| Library partition mounts | n/a | Pass | Pass | Pass |
| Kiwix engine and encyclopedia search | n/a | Pass | Pass | Pass |
| Safety banner on encyclopedia pages | n/a | Pass | Pass | Pass |
| Combined search (40 results for "water") | n/a | Pass | Pass | Pass |
| Map renders features | n/a | Pass | Pass | Pass |

The Secure Boot column for desktop, library, search and maps comes from a run with persistence turned off. In runs with persistence on, the prompt appeared but test keystrokes never reached it.

## Other checks

| Check | Result |
|---|---|
| USB writer refusal tests | 16 of 16 pass, including a regression test for a pipefail bug that could have let the system disk through |
| shellcheck | Clean, 28 scripts |
| Portable Almanac on macOS (arm64, native) | Portal, Kiwix search and map byte-ranges pass |
| Library audit | 9 of 9 files verify against the manifest |
| Source verification | 71 of 72 sources verified (65 content items, 6 tools), 1 failed (`content/UNVERIFIED.md`) |

## Not tested

- A physical USB stick or real PC. `build/write-usb.sh` only ran against a loop device.
- `START-WINDOWS.bat` on Windows. The Windows binaries are built and identified as valid, but were not run.
- The complete Lite, Standard or Full library downloads. Only a 302 MB sample was downloaded.
- Standard and Full ISOs. They use the same steps with a different tier name.
- The Safe graphics, Load to RAM and Memory test boot entries.
- The AI assistant, radio tools against hardware, and battery saver on a real laptop.

### Onn 128 GB stick, 2026-11-21

Written with `usb-from-mac.sh --reuse-image`, then checked with `--verify-only` after the stick dropped off a USB hub during the first check. The MBR and system partitions match the image byte for byte, and the library audit is 56/56. The stick has not yet been booted on real hardware.
