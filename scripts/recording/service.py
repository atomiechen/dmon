"""A small foreground service used by the recording fixture."""

import os
import sys
import time

name = sys.argv[1]
try:
    for tick in range(3600):
        print(f"{name} pid={os.getpid()} tick={tick:03d}", flush=True)
        time.sleep(1)
except KeyboardInterrupt:
    print(f"{name} stopped", flush=True)
