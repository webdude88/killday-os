#!/usr/bin/env python3
"""End-to-end boot test of a Kill-Day USB image under QEMU."""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from PIL import Image

from browser import Browser

IMAGE = Path("/build/test/killday-test.img")
PASSPHRASE = Path("/build/test/passphrase").read_text()
OUT = Path("out/test-results")
PORT = 18642
BOOT_TIMEOUT = 1500
PROMPT_PIXEL = (0xE6, 0xEB, 0xE0)
RETRY_PIXEL = (0xFF, 0x3A, 0x4F)
KEY_NAMES = {"-": "minus"}
OVMF = {
    "uefi": ("/usr/share/OVMF/OVMF_CODE_4M.fd", "/usr/share/OVMF/OVMF_VARS_4M.fd"),
    "secureboot": ("/usr/share/OVMF/OVMF_CODE_4M.secboot.fd", "/usr/share/OVMF/OVMF_VARS_4M.ms.fd"),
}


class VM:
    def __init__(self, mode, name):
        self.mode, self.name = mode, name
        self.tmp = Path(tempfile.mkdtemp())
        self.serial = self.tmp / "serial.log"
        self.qmp_path = self.tmp / "qmp.sock"
        machine = "pc"
        args = []
        if mode == "iso":
            iso = next(Path("out").glob("killday-os-*.iso"))
            args += ["-cdrom", str(iso), "-boot", "d"]
        if mode in OVMF:
            code, variables = OVMF[mode]
            local_vars = self.tmp / "vars.fd"
            shutil.copy(variables, local_vars)
            machine = "q35,smm=on" if mode == "secureboot" else "q35"
            if mode == "secureboot":
                args += ["-global", "driver=cfi.pflash01,property=secure,value=on"]
            args += ["-drive", f"if=pflash,format=raw,readonly=on,file={code}",
                     "-drive", f"if=pflash,format=raw,file={local_vars}"]
        args += ["-machine", machine, "-cpu", "max", "-accel", "tcg,thread=multi", "-smp", "4", "-m", "4096",
                 "-display", "none", "-vga", "std", "-serial", f"file:{self.serial}",
                 "-qmp", f"unix:{self.qmp_path},server,nowait",
                 "-netdev", f"user,id=n0,hostfwd=tcp:0.0.0.0:{PORT}-:8642",
                 "-device", "e1000,netdev=n0"]
        if mode != "iso":
            args += ["-device", "qemu-xhci,id=xhci", "-drive", f"if=none,id=stick,format=raw,file={IMAGE}",
                     "-device", "usb-storage,bus=xhci.0,drive=stick,removable=on,bootindex=1"]
        self.proc = subprocess.Popen(["qemu-system-x86_64", *args])
        for _ in range(100):
            if self.qmp_path.exists():
                break
            time.sleep(0.2)
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.connect(str(self.qmp_path))
        self.reader = self.sock.makefile()
        self.reader.readline()
        self.qmp("qmp_capabilities")

    def qmp(self, command, **arguments):
        self.sock.sendall(json.dumps({"execute": command, "arguments": arguments}).encode() + b"\n")
        while True:
            reply = json.loads(self.reader.readline())
            if "return" in reply or "error" in reply:
                return reply

    def screenshot(self, label):
        OUT.mkdir(parents=True, exist_ok=True)
        ppm = self.tmp / "screen.ppm"
        self.qmp("screendump", filename=str(ppm))
        time.sleep(0.5)
        image = Image.open(ppm).convert("RGB")
        image.save(OUT / f"{self.name}-{label}.png")
        return image

    def type_text(self, text):
        # Clear anything already in the field, such as keys from a lost attempt.
        for _ in range(40):
            self.qmp("send-key", keys=[{"type": "qcode", "data": "backspace"}])
            time.sleep(0.05)
        for char in text:
            key = KEY_NAMES.get(char, char)
            self.qmp("send-key", keys=[{"type": "qcode", "data": key}], **{"hold-time": 40})
            time.sleep(0.12)
        self.qmp("send-key", keys=[{"type": "qcode", "data": "ret"}])

    def log(self):
        return self.serial.read_text(errors="ignore") if self.serial.exists() else ""

    def stop(self):
        self.proc.terminate()
        try:
            self.proc.wait(30)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        shutil.copy(self.serial, OUT / f"{self.name}-serial.log")


def prompt_visible(image):
    return sum(1 for pixel in image.getdata() if pixel == PROMPT_PIXEL) > 200


def retry_visible(image):
    """The "Retry? [Y/n]" question after a wrong passphrase. The red line stays up
    after answering, so it only counts while the passphrase prompt is gone."""
    red = sum(1 for pixel in image.crop((0, image.height * 7 // 8, image.width, image.height)).getdata() if pixel == RETRY_PIXEL)
    return red > 100 and not prompt_visible(image)


def boot(vm, wrong_first=False):
    """Waits for the probe to finish, typing the passphrase when the prompt shows."""
    start = time.time()
    typed = False
    typed_at = 0
    retypes = 0
    retries = 0
    grabbed_splash = False
    while time.time() - start < BOOT_TIMEOUT:
        if "KD-SELFTEST done" in vm.log():
            return True, time.time() - start
        if vm.proc.poll() is not None:
            raise RuntimeError("QEMU exited early")
        image = vm.screenshot("latest")
        if not grabbed_splash and image.getpixel((10, 10)) == (0x0B, 0x0F, 0x0C) and time.time() - start > 45:
            vm.screenshot("splash")
            grabbed_splash = True
        if retry_visible(image) and retries < 3:
            # A rejected passphrase asks "Retry? [Y/n]". Answer it and type again
            # once the prompt is back.
            retries += 1
            vm.retries = retries
            vm.screenshot(f"retry-{retries}")
            vm.qmp("send-key", keys=[{"type": "qcode", "data": "y"}])
            typed = False
            time.sleep(8)
            continue
        if not typed and (prompt_visible(image) or "Please unlock disk" in vm.log()):
            vm.screenshot("passphrase-prompt")
            time.sleep(2)
            if wrong_first:
                # Key derivation is slow under emulation, so wait for the rejection
                # rather than for a fixed time, and type again if the keys were lost.
                for _ in range(3):
                    vm.type_text("wrongphrase")
                    waited = time.time()
                    while time.time() - waited < 150 and not retry_visible(vm.screenshot("latest")):
                        time.sleep(4)
                    if retry_visible(vm.screenshot("wrong-passphrase")):
                        break
                wrong_first = False
                continue
            vm.type_text(PASSPHRASE)
            typed = True
            typed_at = time.time()
        elif typed and retypes < 3 and time.time() - typed_at > 90 and prompt_visible(image):
            # Under emulation the prompt can be drawn before it reads keys, so the
            # first attempt is lost. Clear whatever arrived and type it again.
            retypes += 1
            vm.screenshot(f"retype-{retypes}")
            vm.type_text(PASSPHRASE)
            typed_at = time.time()
            print(f"  note  {vm.name}: passphrase retyped ({retypes})", flush=True)
        time.sleep(4)
    return False, time.time() - start


def probe_values(log):
    return dict(re.findall(r"KD-SELFTEST (\w[\w-]*)=(\S+)", log))


def http(path):
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=120) as response:
        return response.status, response.read().decode("utf-8", "ignore")


def green_pixels(image):
    return sum(1 for pixel in image.getdata() if pixel == (0x8C, 0xFF, 0x5A))


def run_iso():
    """Boots the plain ISO: no persistence partition and no library present."""
    results = {}
    vm = VM("iso", "iso")
    try:
        menu_seen = False
        for _ in range(45):
            image = vm.screenshot("latest")
            if not menu_seen and green_pixels(image) > 2000 and image.getpixel((5, 5)) != (0, 0, 0):
                vm.screenshot("grub-menu")
                menu_seen = True
                vm.qmp("send-key", keys=[{"type": "qcode", "data": "ret"}])
                break
            time.sleep(2)
        results["themed GRUB menu appears"] = menu_seen
        started = time.time()
        desktop = False
        while time.time() - started < 900 and not desktop:
            time.sleep(10)
            image = vm.screenshot("latest")
            desktop = green_pixels(image) > 1500 and image.getpixel((5, 5)) != (0x0B, 0x0F, 0x0C)
        vm.screenshot("desktop")
        results["boots to the Almanac without USB partitions"] = desktop
    finally:
        vm.stop()
    for name, passed in results.items():
        print(f"  {'PASS' if passed else 'FAIL'}  iso: {name}", flush=True)
    return results


def run(mode):
    results = {}

    def check(name, passed, detail=""):
        results[name] = bool(passed)
        print(f"  {'PASS' if passed else 'FAIL'}  {mode}: {name}  {detail}", flush=True)

    first = VM(mode, f"{mode}-boot1")
    try:
        finished, seconds = boot(first)
        check("boots to desktop and probe completes", finished, f"{seconds:.0f}s under software emulation")
        values = probe_values(first.log())
        check("persistence unlocked with passphrase", values.get("persistence") == "true")
        check("library partition mounted", values.get("library") == "mounted")
        check("portal answers", values.get("portal") == "200")
        check("desktop running", values.get("desktop") == "up")
        check("kiwix engine running", values.get("kiwix") == "true")
        time.sleep(30)
        first.screenshot("desktop")

        status, body = http("/")
        check("portal reachable from host", status == 200 and "Kill-Day Almanac" in body)
        _, feed = http("/kiwix/search?pattern=antenna&pageLength=5&format=xml")
        link = re.search(r"<link>(/kiwix/content/[^<]+)</link>", feed)
        check("encyclopedia search returns results", link is not None)
        if link:
            _, article = http(link.group(1))
            check("safety banner added to encyclopedia pages", "REFERENCE ONLY" in article)
        OUT.mkdir(parents=True, exist_ok=True)
        browser = Browser()
        try:
            browser.open(f"http://127.0.0.1:{PORT}/?q=water")
            count = browser.wait_for("document.body.dataset.searchDone", 120)
            check("combined search returns results", count and int(count) > 0, f"{count} results")
            browser.screenshot(OUT / f"{mode}-search.png")
            browser.open(f"http://127.0.0.1:{PORT}/map.html")
            state = browser.wait_for("document.body.dataset.mapState", 180)
            check("map renders features", state == "rendered", f"state={state}")
            browser.screenshot(OUT / f"{mode}-map.png")
        finally:
            browser.close()
        # A later firmware mode shares the image, so it may find an earlier marker.
        check("persistent home is writable", values.get("marker") in ("absent", "present"))
        time.sleep(50)
        first.screenshot("desktop-bare")
    finally:
        first.stop()

    time.sleep(3)
    second = VM(mode, f"{mode}-boot2")
    try:
        finished, _ = boot(second, wrong_first=True)
        values = probe_values(second.log())
        check("second boot completes", finished)
        check("wrong passphrase can be retried", values.get("persistence") == "true" and getattr(second, "retries", 0) >= 1)
        check("files persist across reboot", values.get("marker") == "present")
    finally:
        second.stop()
    return results


def main():
    modes = " ".join(sys.argv[1:]).split()
    failures = 0
    for mode in modes:
        print(f"== {mode}", flush=True)
        results = run_iso() if mode == "iso" else run(mode)
        failures += sum(1 for passed in results.values() if not passed)
    print(f"\n{'ALL PASSED' if not failures else f'{failures} CHECK(S) FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
