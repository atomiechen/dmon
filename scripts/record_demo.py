"""Record real dmon commands with VHS and tmux (macOS/Linux)."""

import argparse
from pathlib import Path
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

import psutil


def record(mode):
    for executable in ("vhs", "tmux", "ffmpeg", "ttyd"):
        if not shutil.which(executable):
            raise SystemExit(f"Missing recording tool: {executable}")
    repo = Path(__file__).resolve().parents[1]
    root = Path(tempfile.mkdtemp(prefix="dmon-demo-", dir="/tmp"))
    source = repo / "scripts" / "recording"
    for name in ("service.py", "panels.py", "appearance.tape"):
        shutil.copy2(source / name, root / name)
    shutil.copy2(source / "config.yaml", root / "dmon.yaml")
    shutil.copy2(source / f"{mode}.tape", root / "demo.tape")
    # A private tmux socket prevents interference with the user's sessions.
    socket = str(root / "tmux.sock")
    tmux = "tmux -S " + shlex.quote(socket)
    python = shlex.quote(sys.executable)
    log_names = ("quick", "api") if mode == "everyday" else ("api", "worker")
    (root / "layout.sh").write_text(f"""#!/bin/bash
set -eu
{tmux} -f /dev/null new-session -d -s demo -x 150 -y 45 'bash --noprofile --norc'
{tmux} set-option -g status off
{tmux} set-option -g default-terminal xterm-256color
{tmux} split-window -v -t demo:0.0 -p 35 '{python} panels.py files'
{tmux} split-window -h -t demo:0.1 -p 72 '{python} panels.py {log_names[0]}'
{tmux} split-window -h -t demo:0.2 -p 50 '{python} panels.py {log_names[1]}'
{tmux} send-keys -t demo:0.0 'export PS1="\\[\\e[36m\\]$ \\[\\e[0m\\]"; clear' Enter
{tmux} pipe-pane -t demo:0.0 -O "cat >> terminal.ansi"
{tmux} select-pane -t demo:0.0
exec {tmux} attach-session -t demo
""")
    env = dict(
        os.environ,
        PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"],
    )
    env.pop("NO_COLOR", None)
    env.pop("ANSI_COLORS_DISABLED", None)
    env["TERM"] = "xterm-256color"
    tracked = []
    snapshots = []
    recording = None
    try:
        recording = subprocess.Popen(["vhs", "demo.tape"], cwd=root, env=env)
        deadline = time.monotonic() + 240
        while recording.poll() is None:
            state = root / ".dmon/dev.stack.json"
            if state.exists():
                data = json.loads(state.read_text())
                snapshots.append(data)
                tracked.extend([data, *data.get("tasks", [])])
            for path in (root / ".dmon").glob("*.meta.json"):
                try:
                    tracked.append(json.loads(path.read_text()))
                except FileNotFoundError:
                    pass
            if time.monotonic() > deadline:
                raise TimeoutError("Recording timed out")
            time.sleep(0.2)
        if recording.returncode:
            raise RuntimeError("VHS recording failed")
        transcript = (root / "terminal.ansi").read_text()
        if "Traceback" in transcript or "error:" in transcript:
            raise RuntimeError("CLI error in recording; inspect terminal.ansi")
        if not tracked:
            raise RuntimeError("No managed process was observed")
        if "\x1b[" not in transcript:
            raise RuntimeError("Recording did not retain ANSI colors")
        if mode == "stack":
            ready = [s for s in snapshots if s.get("state") == "running"]
            degraded = [s for s in snapshots if s.get("state") == "degraded"]

            def member(snapshot, name):
                task = next(t for t in snapshot["tasks"] if t["task"] == name)
                return task["pid"], task["create_time"]

            if not ready or not degraded:
                raise RuntimeError("Recording did not show startup and degradation")
            if member(ready[0], "api") != member(ready[-1], "api"):
                raise RuntimeError("API identity changed during recording")
            if member(ready[0], "worker") == member(ready[-1], "worker"):
                raise RuntimeError("Recording did not replace worker")
            (root / "states.json").write_text(json.dumps(snapshots, indent=2))
    finally:
        if recording is not None and recording.poll() is None:
            recording.terminate()
            recording.wait(timeout=10)
        state = root / ".dmon/dev.stack.json"
        if state.exists():
            data = json.loads(state.read_text())
            tracked.extend([data, *data.get("tasks", [])])
        cleanup = subprocess.run(
            [sys.executable, "-m", "dmon", "stack", "down", "dev", "-c", str(root)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        subprocess.run(
            [sys.executable, "-m", "dmon", "stop", "--all", "-c", str(root)],
            capture_output=True,
            timeout=30,
        )
        subprocess.run(["tmux", "-S", socket, "kill-server"], capture_output=True)
        survivors = []
        for identity in tracked:
            try:
                p = psutil.Process(identity["pid"])
                if (
                    p.create_time() == identity["create_time"]
                    and p.status() != psutil.STATUS_ZOMBIE
                ):
                    survivors.append(identity)
            except psutil.NoSuchProcess:
                pass
        (root / "cleanup.json").write_text(
            json.dumps(
                {
                    "survivors": survivors,
                    "stdout": cleanup.stdout,
                    "stderr": cleanup.stderr,
                },
                indent=2,
            )
        )
        if survivors:
            raise RuntimeError(f"Recording cleanup incomplete: {root}")
        print(f"{mode} recording and cleanup results: {root}")
    return root


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", choices=["everyday", "stack", "both"], default="both")
    args = parser.parse_args()
    for mode in ["everyday", "stack"] if args.demo == "both" else [args.demo]:
        record(mode)
