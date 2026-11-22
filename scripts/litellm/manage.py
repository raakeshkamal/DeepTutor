"""Manage the private local proxy without changing DeepTutor or its model settings."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

HOME = Path(os.environ.get("DEEPTUTOR_HOME", str(Path.home() / "deeptutor"))).resolve()
ROOT = HOME / "litellm"
PID_FILE = ROOT / "proxy.pid"
KEY_FILE = ROOT / "proxy.key"
SERVER = Path(__file__).with_name("serve.py").resolve()
PYTHON = Path.home() / ".local/share/uv/tools/litellm/bin/python"
MODELS = {"deeptutor-chat", "deeptutor-openrouter", "deeptutor-embeddings"}


def managed_pid() -> int | None:
    try:
        pid = int(PID_FILE.read_text().strip())
        command = subprocess.check_output(["ps", "-p", str(pid), "-o", "command="], text=True)
        return pid if str(SERVER) in command else None
    except (OSError, ValueError, subprocess.CalledProcessError):
        return None


def ready() -> bool:
    try:
        key = KEY_FILE.read_text().strip()
        request = urllib.request.Request(
            "http://127.0.0.1:4000/v1/models", headers={"Authorization": f"Bearer {key}"}
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            names = {m["id"] for m in json.load(response)["data"]}
        return MODELS <= names
    except (OSError, ValueError, KeyError, urllib.error.URLError):
        return False


def start() -> None:
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    if managed_pid() and ready():
        print("LiteLLM is already ready on 127.0.0.1:4000.")
        return
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 4000)) == 0:
            raise RuntimeError("Port 4000 is occupied; refusing to reuse or stop an unknown service.")
    if not PYTHON.is_file():
        raise RuntimeError("Install LiteLLM 1.101.0 through uv tool before starting.")
    if not KEY_FILE.exists():
        fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as output:
            output.write("sk-dt-" + secrets.token_urlsafe(32) + "\n")
    with (ROOT / "proxy.log").open("a") as log:
        process = subprocess.Popen(
            [str(PYTHON), str(SERVER)], stdout=log, stderr=log,
            env={**os.environ, "DEEPTUTOR_HOME": str(HOME)},
            cwd=SERVER.parent, start_new_session=True,
        )
    PID_FILE.write_text(str(process.pid) + "\n")
    for _ in range(120):
        if process.poll() is not None:
            PID_FILE.unlink(missing_ok=True)
            raise RuntimeError("LiteLLM exited; inspect ~/deeptutor/litellm/proxy.log privately.")
        if ready():
            print(f"LiteLLM is ready on 127.0.0.1:4000 (PID {process.pid}).")
            return
        time.sleep(0.5)
    process.terminate()
    process.wait(timeout=15)
    PID_FILE.unlink(missing_ok=True)
    raise RuntimeError("LiteLLM did not become ready; DeepTutor settings were not changed.")


def stop() -> None:
    pid = managed_pid()
    if pid is not None:
        os.kill(pid, signal.SIGTERM)
        for _ in range(100):
            if managed_pid() is None:
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("LiteLLM has not stopped; refusing to start another instance.")
    PID_FILE.unlink(missing_ok=True)
    print("LiteLLM stopped.")


def main() -> None:
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["start", "stop", "status", "restart"])
    args = parser.parse_args()
    if args.operation == "status":
        ok = managed_pid() is not None and ready()
        print("LiteLLM is ready." if ok else "LiteLLM is not ready.")
        raise SystemExit(0 if ok else 1)
    if args.operation in {"stop", "restart"}:
        stop()
    if args.operation in {"start", "restart"}:
        start()


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
