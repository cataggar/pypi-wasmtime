#!/usr/bin/env python3
"""Download wasmtime release assets and repackage them as Python wheels."""

# /// script
# requires-python = ">=3.12"
# dependencies = ["requests"]
# ///

import hashlib
import io
import stat
import sys
import tarfile
import zipfile
from base64 import urlsafe_b64encode
from pathlib import Path

import requests  # type: ignore[import-untyped]

IMPORT_NAME = "wasmtime_cli"
DIST_NAME = "wasmtime_bin"
WASMTIME_REPO = "bytecodealliance/wasmtime"

PLATFORMS = {
    "x86_64-linux": {
        "ext": ".tar.xz",
        "tag": "manylinux_2_17_x86_64.manylinux2014_x86_64",
        "binary": "wasmtime",
    },
    "aarch64-linux": {
        "ext": ".tar.xz",
        "tag": "manylinux_2_17_aarch64.manylinux2014_aarch64",
        "binary": "wasmtime",
    },
    "x86_64-musl": {
        "ext": ".tar.xz",
        "tag": "musllinux_1_1_x86_64",
        "binary": "wasmtime",
    },
    "aarch64-musl": {
        "ext": ".tar.xz",
        "tag": "musllinux_1_1_aarch64",
        "binary": "wasmtime",
    },
    "x86_64-macos": {
        "ext": ".tar.xz",
        "tag": "macosx_10_9_x86_64",
        "binary": "wasmtime",
    },
    "aarch64-macos": {
        "ext": ".tar.xz",
        "tag": "macosx_11_0_arm64",
        "binary": "wasmtime",
    },
    "x86_64-windows": {
        "ext": ".zip",
        "tag": "win_amd64",
        "binary": "wasmtime.exe",
    },
    "aarch64-windows": {
        "ext": ".zip",
        "tag": "win_arm64",
        "binary": "wasmtime.exe",
    },
}


def sha256_digest(data: bytes) -> str:
    """Return url-safe base64 sha256 digest (no padding)."""
    return urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()


def download_asset(version: str, platform_key: str, ext: str) -> bytes:
    """Download a wasmtime release asset."""
    asset_name = f"wasmtime-v{version}-{platform_key}{ext}"
    url = f"https://github.com/{WASMTIME_REPO}/releases/download/v{version}/{asset_name}"
    print(f"  Downloading {asset_name} ...")
    resp = requests.get(url, allow_redirects=True, timeout=300)
    resp.raise_for_status()
    return resp.content


def extract_binary(data: bytes, ext: str, binary_name: str) -> bytes:
    """Extract just the binary from an archive."""
    if ext == ".tar.xz":
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:xz") as tf:
            for member in tf.getmembers():
                if member.name == binary_name or member.name.endswith(f"/{binary_name}"):
                    f = tf.extractfile(member)
                    if f is not None:
                        return f.read()
    elif ext == ".zip":
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for name in zf.namelist():
                if name == binary_name or name.endswith(f"/{binary_name}"):
                    return zf.read(name)

    raise FileNotFoundError(f"Binary {binary_name!r} not found in archive")


_EXEC_ATTR = (
    stat.S_IFREG | stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
) << 16
_FILE_ATTR = (stat.S_IFREG | stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH) << 16


def build_wheel(version: str, platform_key: str, info: dict[str, str], dist_dir: Path) -> Path:
    """Build a single platform wheel with native binary in data/scripts/."""
    ext = info["ext"]
    platform_tag = info["tag"]
    binary_name = info["binary"]

    data = download_asset(version, platform_key, ext)
    binary_data = extract_binary(data, ext, binary_name)

    data_scripts_dir = f"{DIST_NAME}-{version}.data/scripts"
    dist_info_dir = f"{DIST_NAME}-{version}.dist-info"

    # Collect wheel entries: (arcname, data_bytes, is_executable)
    entries: list[tuple[str, bytes, bool]] = []

    # Add __init__.py
    init_py = Path(__file__).resolve().parent.parent / "python" / IMPORT_NAME / "__init__.py"
    entries.append(
        (f"{IMPORT_NAME}/__init__.py", init_py.read_bytes(), False)
    )

    # Native binary goes in data/scripts/ — pip copies it directly to bin/Scripts
    entries.append((f"{data_scripts_dir}/{binary_name}", binary_data, True))

    readme_path = Path(__file__).resolve().parent.parent / "README.md"
    readme_text = readme_path.read_text(encoding="utf-8")

    metadata = (
        f"Metadata-Version: 2.4\n"
        f"Name: wasmtime-bin\n"
        f"Version: {version}\n"
        f"Summary: Wasmtime CLI repackaged as Python wheels\n"
        f"Home-page: https://github.com/bytecodealliance/wasmtime\n"
        f"License: Apache-2.0 WITH LLVM-exception\n"
        f"Requires-Python: >=3.9\n"
        f"Description-Content-Type: text/markdown\n"
        f"\n"
        f"{readme_text}"
    )
    entries.append((f"{dist_info_dir}/METADATA", metadata.encode(), False))

    wheel_meta = (
        f"Wheel-Version: 1.0\n"
        f"Generator: build_wheels.py\n"
        f"Root-Is-Purelib: false\n"
        f"Tag: py3-none-{platform_tag}\n"
    )
    entries.append((f"{dist_info_dir}/WHEEL", wheel_meta.encode(), False))

    # No entry_points.txt — binary is installed directly via data/scripts

    # Build RECORD
    records: list[str] = []
    for arcname, file_data, _ in entries:
        digest = sha256_digest(file_data)
        records.append(f"{arcname},sha256={digest},{len(file_data)}")
    records.append(f"{dist_info_dir}/RECORD,,")
    record_data = ("\n".join(records) + "\n").encode()
    entries.append((f"{dist_info_dir}/RECORD", record_data, False))

    # Write wheel zip
    wheel_name = f"{DIST_NAME}-{version}-py3-none-{platform_tag}.whl"
    wheel_path = dist_dir / wheel_name
    with zipfile.ZipFile(wheel_path, "w", zipfile.ZIP_DEFLATED) as whl:
        for arcname, file_data, executable in entries:
            zi = zipfile.ZipInfo(arcname)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = _EXEC_ATTR if executable else _FILE_ATTR
            whl.writestr(zi, file_data)

    print(f"  Built {wheel_name} ({wheel_path.stat().st_size / 1024 / 1024:.1f} MB)")
    return wheel_path


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <version>")
        print(f"Example: {sys.argv[0]} 42.0.1")
        sys.exit(1)

    version = sys.argv[1]
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)

    print(f"Building wheels for wasmtime v{version}\n")

    wheels: list[Path] = []
    for platform_key, info in PLATFORMS.items():
        print(f"[{platform_key}]")
        wheel = build_wheel(version, platform_key, info, dist_dir)
        wheels.append(wheel)
        print()

    print(f"Done! {len(wheels)} wheels in {dist_dir}/")
    for w in wheels:
        print(f"  {w.name}")


if __name__ == "__main__":
    main()
