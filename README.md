# HW Monitor

Minimal hardware monitor for Windows. CPU/GPU temps and usage. No dependencies.

![demo](https://via.placeholder.com/200x60/1a1a1a/ffffff?text=CPU:+65°C+|+23%+GPU:+52°C+|+45%)

## Install

**Executable**: Download `hwmon.exe` from releases, run it.

**From source**:
```bash
python -m hwmon
```

**Build yourself**:
```bash
pip install pyinstaller
build.bat
```

## Controls

- Drag anywhere to move
- Right-click to exit

## Requirements

- Windows 10+
- NVIDIA drivers for GPU temp (AMD/Intel may show N/A)

## Structure

| File | Purpose |
|------|---------|
| `main.py` | GUI (tkinter) |
| `sensors.py` | Sensor backend |
| `pdh_counters.py` | Windows PDH API |
| `nvapi.py` | NVIDIA API |

## License

MIT
