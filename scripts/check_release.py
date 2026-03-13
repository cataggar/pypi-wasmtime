#!/usr/bin/env python3
"""Check for new wasmtime releases and signal when a new tag should be created."""

# /// script
# requires-python = ">=3.12"
# dependencies = ["requests"]
# ///

import logging
import os
import sys
from typing import Any

import requests  # type: ignore[import-untyped]

UPSTREAM_REPO = "bytecodealliance/wasmtime"

# Must match PLATFORMS in build_wheels.py — if platforms change there, update here too.
EXPECTED_ASSETS: list[tuple[str, str]] = [
    ("x86_64-linux", ".tar.xz"),
    ("aarch64-linux", ".tar.xz"),
    ("x86_64-musl", ".tar.xz"),
    ("aarch64-musl", ".tar.xz"),
    ("x86_64-macos", ".tar.xz"),
    ("aarch64-macos", ".tar.xz"),
    ("x86_64-windows", ".zip"),
    ("aarch64-windows", ".zip"),
]

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def github_headers() -> dict[str, str]:
    """Build headers for GitHub API requests."""
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_latest_release() -> dict[str, Any]:
    """Fetch the latest non-prerelease, non-draft release from upstream."""
    url = f"https://api.github.com/repos/{UPSTREAM_REPO}/releases/latest"
    resp = requests.get(url, headers=github_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def tag_exists(repo: str, tag: str) -> bool:
    """Check if a git tag already exists in our repository."""
    url = f"https://api.github.com/repos/{repo}/git/ref/tags/{tag}"
    resp = requests.get(url, headers=github_headers(), timeout=30)
    if resp.status_code == 200:
        return True
    if resp.status_code == 404:
        return False
    resp.raise_for_status()
    return False  # unreachable, but makes mypy happy


def validate_assets(release: dict[str, Any], version: str) -> bool:
    """Verify that all expected platform archives are present in the release."""
    asset_names: set[str] = {a["name"] for a in release.get("assets", [])}
    log.info("Release has %d total assets; checking %d required assets:", len(asset_names), len(EXPECTED_ASSETS))

    missing: list[str] = []
    for platform_key, ext in EXPECTED_ASSETS:
        expected = f"wasmtime-v{version}-{platform_key}{ext}"
        if expected in asset_names:
            log.info("  ✓ %s", expected)
        else:
            log.error("  ✗ MISSING: %s", expected)
            missing.append(expected)

    if missing:
        log.error("%d of %d expected assets are missing", len(missing), len(EXPECTED_ASSETS))
        return False

    log.info("All %d expected assets are present", len(EXPECTED_ASSETS))
    return True


def set_github_output(name: str, value: str) -> None:
    """Write a key=value pair to $GITHUB_OUTPUT for use in subsequent workflow steps."""
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a") as f:
            f.write(f"{name}={value}\n")
    else:
        log.info("GITHUB_OUTPUT not set (running locally?); would set %s=%s", name, value)


def main() -> None:
    our_repo = os.environ.get("GITHUB_REPOSITORY", "cataggar/pypi-wasmtime")
    log.info("Checking for new %s releases...", UPSTREAM_REPO)

    release = get_latest_release()
    tag_name = release["tag_name"]  # e.g. "v42.0.1"

    if not tag_name.startswith("v"):
        log.error("Unexpected tag format: %s", tag_name)
        sys.exit(1)

    version = tag_name[1:]  # strip leading "v"
    log.info("Latest upstream release: %s (version %s)", tag_name, version)

    if tag_exists(our_repo, tag_name):
        log.info("Tag %s already exists in %s — nothing to do", tag_name, our_repo)
        set_github_output("new_version", "")
        return

    log.info("Tag %s does not exist in %s — validating release assets...", tag_name, our_repo)

    if not validate_assets(release, version):
        log.error("Asset validation failed for %s — will not create tag", tag_name)
        sys.exit(1)

    log.info("New release %s is ready for tagging", tag_name)
    set_github_output("new_version", tag_name)


if __name__ == "__main__":
    main()
