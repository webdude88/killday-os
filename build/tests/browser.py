#!/usr/bin/env python3
"""Drives headless Chromium over DevTools, so checks can wait for real page state."""
import base64
import json
import subprocess
import tempfile
import time
import urllib.request

from websockets.sync.client import connect


class Browser:
    def __init__(self, port=9222):
        self.profile = tempfile.TemporaryDirectory()
        self.proc = subprocess.Popen(
            ["chromium", "--headless=new", "--no-sandbox", "--enable-unsafe-swiftshader", "--window-size=1280,900",
             f"--remote-debugging-port={port}", f"--user-data-dir={self.profile.name}", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        target = None
        for _ in range(100):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json") as response:
                    pages = [t for t in json.load(response) if t["type"] == "page"]
                if pages:
                    target = pages[0]
                    break
            except OSError:
                pass
            time.sleep(0.3)
        if target is None:
            raise RuntimeError("Chromium did not start")
        self.socket = connect(target["webSocketDebuggerUrl"], max_size=None, open_timeout=30)
        self.next_id = 0

    def call(self, method, **params):
        self.next_id += 1
        self.socket.send(json.dumps({"id": self.next_id, "method": method, "params": params}))
        while True:
            reply = json.loads(self.socket.recv(timeout=180))
            if reply.get("id") == self.next_id:
                return reply.get("result", {})

    def open(self, url):
        self.call("Page.navigate", url=url)

    def evaluate(self, expression):
        result = self.call("Runtime.evaluate", expression=expression, returnByValue=True)
        return result.get("result", {}).get("value")

    def wait_for(self, expression, timeout):
        """Returns the first truthy value of expression, or None after timeout."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            value = self.evaluate(expression)
            if value:
                return value
            time.sleep(1)
        return None

    def screenshot(self, path):
        data = self.call("Page.captureScreenshot", format="png")["data"]
        with open(path, "wb") as handle:
            handle.write(base64.b64decode(data))

    def close(self):
        self.proc.terminate()
        self.proc.wait(20)
