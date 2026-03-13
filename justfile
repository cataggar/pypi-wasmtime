# Show the current version
version:
    uvx --with hatch-vcs hatchling version

# Build wheels for a specific wasmtime version (e.g., just build 42.0.1)
build version:
    uv run scripts/build_wheels.py {{version}}

# Clean build artifacts
clean:
    rm -rf dist/
