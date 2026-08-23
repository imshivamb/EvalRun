"""Interactive terminal progress indicator for long model evaluations."""

import itertools
import sys
import threading
import time
from typing import Callable, TypeVar

T = TypeVar("T")


def run_with_progress(label: str, operation: Callable[[], T]) -> T:
    """Run an operation while showing a live spinner in an interactive terminal."""
    interactive = bool(getattr(sys.stdout, "isatty", lambda: False)())
    if not interactive:
        return operation()

    stop = threading.Event()
    frames = itertools.cycle("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")
    statuses = itertools.cycle(("contacting model", "running agent", "scoring response", "writing report"))
    started = time.monotonic()

    def render() -> None:
        while not stop.wait(0.35):
            elapsed = int(time.monotonic() - started)
            sys.stdout.write(f"\r[evalrun] {next(frames)} {label} — {next(statuses)} ({elapsed}s)")
            sys.stdout.flush()

    thread = threading.Thread(target=render, daemon=True)
    thread.start()
    try:
        return operation()
    finally:
        stop.set()
        thread.join(timeout=1.0)
        elapsed = time.monotonic() - started
        sys.stdout.write(f"\r[evalrun] ✓ {label} completed in {elapsed:.1f}s\033[K\n")
        sys.stdout.flush()
