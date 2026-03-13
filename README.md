# wasmtime-cli

[Wasmtime](https://github.com/bytecodealliance/wasmtime) CLI repackaged as Python wheels for easy installation via `pip` or `uv`.

Wasmtime is a fast and secure runtime for WebAssembly.

## Install

```sh
uv tool install wasmtime-cli
```

## Usage

```sh
wasmtime run hello.wasm
```

## Supported Platforms

| Platform | Wheel tag |
|----------|-----------|
| Linux x64 | `manylinux_2_17_x86_64` |
| Linux ARM64 | `manylinux_2_17_aarch64` |
| Linux x64 (musl) | `musllinux_1_1_x86_64` |
| Linux ARM64 (musl) | `musllinux_1_1_aarch64` |
| macOS x64 | `macosx_10_9_x86_64` |
| macOS ARM64 | `macosx_11_0_arm64` |
| Windows x64 | `win_amd64` |
| Windows ARM64 | `win_arm64` |

## How It Works

This package downloads the official wasmtime release archives from
[bytecodealliance/wasmtime](https://github.com/bytecodealliance/wasmtime/releases)
and repackages each `.tar.xz` / `.zip` as a platform-specific Python wheel.

A thin Python entry point (`console_scripts`) delegates to the native binary,
so `wasmtime` is available on `PATH` after install.

## License

This package redistributes wasmtime under its
[Apache-2.0 WITH LLVM-exception](https://github.com/bytecodealliance/wasmtime/blob/main/LICENSE) license.
