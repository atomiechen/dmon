"""Live file and log panels for the terminal recording; read-only."""

from pathlib import Path
import shutil
import sys
import time


def show(mode):
    print("\033[?25l", end="", flush=True)
    try:
        while True:
            width, height = shutil.get_terminal_size()
            lines = []
            if mode == "files":
                lines = ["PROJECT FILES", "dmon.yaml", "service.py"]
                for directory in (".dmon", "logs"):
                    path = Path(directory)
                    if path.exists():
                        lines.append(directory + "/")
                        lines += [
                            "  " + p.name for p in sorted(path.iterdir()) if p.is_file()
                        ]
            else:
                lines = [f"{mode.upper()} LOG"]
                path = Path("logs") / f"{mode}.log"
                if path.exists():
                    lines += path.read_text(errors="replace").splitlines()[
                        -max(1, height - len(lines)) :
                    ]
            print(
                "\033[H"
                + "\n".join(s[: width - 1] + "\033[K" for s in lines[:height])
                + "\033[J",
                end="",
                flush=True,
            )
            time.sleep(0.3)
    finally:
        print("\033[?25h", end="", flush=True)


if __name__ == "__main__":
    show(sys.argv[1])
