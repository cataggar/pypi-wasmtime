# Show the current version
version:
    uvx --with hatch-vcs hatchling version

# Build wheels for a specific wasmtime version (e.g., just build 42.0.1)
build version:
    uv run scripts/build_wheels.py {{version}}

# Run all checks
check: pyright

# Type check
pyright:
    uvx pyright

# Check for new upstream release
check-release:
    uv run scripts/check_release.py

# Clean build artifacts
clean:
    rm -rf dist/
