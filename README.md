# HW Monitor

Minimal always-on-top hardware monitor for Windows. Pure Python, zero dependencies.

![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue)
![Windows](https://img.shields.io/badge/platform-windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

![Screenshot1](assets/screenshot1.png)

## Features

- CPU temperature & usage
- GPU temperature & usage (NVIDIA, AMD, Intel)
- Network throughput (in/out)
- Borderless, always-on-top overlay

## Install

**Executable**: Get `hwmon.exe` from releases, just run it.

**From source**:
```bash
uv run hwmon
```

**Build yourself**:

You'll need python 3.13 with UV
```bash
.\build.bat
# or
uv run pyinstaller hwmon.spec
```

## Controls

- Drag anywhere to move
- Right-click to exit

## GPU Support

| Vendor | Temp | Usage | Method |
|--------|------|-------|--------|
| NVIDIA | ✓ | ✓ | NVAPI + PDH |
| AMD | ? | ? | ADL + PDH |
| Intel | ~ | ✓ | PDH only |

- Intel iGPU temp depends on thermal zone exposure. May show N/A.
- AMD not tested

## License

MIT
