# Known limitations and ideas for v2

## Limitations

**Content**
- Full-text encyclopedias cannot be filtered article by article. Wikipedia and Wikibooks describe weapons and explosives at an encyclopedic level. Curated documents exclude weapon-building manuals, and `content/sources.json` lists what was left out and why.
- Water and shelter have fewer dedicated manuals than planned. FEMA, CDC and CPSC refuse automated downloads, and the WHO drinking-water guideline did not return a PDF (`content/UNVERIFIED.md`).
- No dedicated public-domain foraging field guide could be verified. The Forest Service GTR-513 is a Pacific Northwest species reference and does not cover look-alikes.
- FM 4-25.11 (2002) is old. It is included beside the current ATP 4-02.11, and medical guidance changes over time.
- ATP 4-02.11 includes combat casualty care aimed at soldiers.
- Khan Academy's newest English ZIM is from 2023.
- Some licenses are non-commercial (iFixit, Khan Academy, LibreTexts, some OpenStax titles). Giving copies to family is fine. Selling this drive would not be.
- Map checksums are computed when each region is extracted, because extracts are built per run.

**Disclaimers**
- Banners are added by the Almanac server. Opening a ZIM directly in the Kiwix app, or a PDF straight from the drive, bypasses them. `START-HERE.html` repeats the warning above each section as a partial mitigation.

**Hardware and boot**
- x86_64 only. Apple Silicon Macs and ARM boards cannot boot it, though they can use the library through START-MAC.
- Passphrase entry under Secure Boot passes in emulation (Plus tier, 2026-11-20) but has not been tried on real hardware. The workarounds are in RUNBOOK section 6.
- The AI assistant gets facts wrong. In testing it muddled the bleach dose for drinking water. It is labelled unreliable everywhere it appears.
- Testing used QEMU, with no physical USB stick or PC.
- Intel Macs and machines with unusual firmware are untested.
- Windows releases before Windows 10 version 1703 show only the first partition of a removable drive, so they may not see the library.
- The MBR partition table caps usable space at 2 TiB.
- Broadcom Wi-Fi chips that need the `broadcom-sta` DKMS driver are not supported.

**System**
- Persistence covers `/home` and saved Wi-Fi networks only. Software installed while running is lost at reboot, which is what lets a new OS version be written without touching your files.
- The library is mounted read-only under Kill-Day OS to protect it from power loss.
- CHIRP, fldigi, direwolf and gqrx are installed, but were not tested against radio hardware.
- `Load to RAM` needs 8 GB or more.

## Ideas for v2
- A map region picker in the portal that does not need the command line.
- Translated library sets (Spanish first).
- Signed releases and a verified USB-to-USB clone tool.
- Per-article content filtering for Wikipedia ZIMs, using a category blocklist.
- A small mesh-messaging app that works over Wi-Fi with no access point.
- A printable field-notes PDF generated from pages you bookmark.
