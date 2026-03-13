"""Wasmtime CLI - a fast and secure runtime for WebAssembly."""

import os
import subprocess
import sys
from pathlib import Path

try:
    from importlib.metadata import version

    __version__ = version("wasmtime-cli")
except Exception:
    __version__ = "0.0.0"

_BIN = "wasmtime.exe" if sys.platform == "win32" else "wasmtime"


def _binary_path() -> Path:
    """Return the path to the wasmtime binary."""
    return Path(__file__).parent / _BIN


def main() -> None:
    """Entry point that delegates to the native binary."""
    binary = _binary_path()
    if not binary.exists():
        print(
            f"wasmtime binary not found at {binary}",
            file=sys.stderr,
        )
        sys.exit(1)
    args = [str(binary), *sys.argv[1:]]
    if sys.platform != "win32":
        os.execv(args[0], args)
    else:
        raise SystemExit(subprocess.call(args))
