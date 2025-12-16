# HW Monitor

A minimal, lightweight hardware monitor for Windows that displays real-time CPU and GPU temperatures and usage percentages. Built using **only Python standard library** (no external dependencies required).

## Features

- **Real-time monitoring** of:
  - CPU temperature and usage
  - GPU temperature (NVIDIA via NVAPI) and usage
- **Zero external dependencies** - uses only Python's built-in libraries
- **Borderless, draggable window** - sleek dark theme, always on top
- **Move anywhere** - click and drag from any part of the window
- **Minimalistic GUI** - clean, simple interface with dark theme
- **Efficient** - low resource usage, updates every 750ms
- **Accurate readings** via native Windows APIs:
  - Performance Data Helper (PDH) for CPU metrics and GPU usage
  - NVAPI for NVIDIA GPU temperatures

## Requirements

- Windows 10 or later
- Python 3.9+
- For NVIDIA GPUs: NVIDIA drivers installed (for GPU temperature)

## Installation

### Option 1: Download Pre-built Executable (Easiest)

1. Download `hwmon.exe` from the releases page
2. Double-click to run - no installation needed!

### Option 2: Run from Source

Clone or download this repository:

```bash
git clone <repository-url>
cd hwmon
```

No additional packages to install! Everything uses Python's standard library.

### Option 3: Build Your Own Executable

1. Install build dependencies:
```bash
pip install pyinstaller
```

2. Run the build script:
```bash
build.bat
```

3. Find the executable in `dist\hwmon.exe`

## Usage

### Running the Executable

Simply double-click `hwmon.exe` - no Python installation required!

### Running from Source

```bash
python monitor.py
```

Or if installed as a package:

```bash
pip install -e .
hwmon
```

The window will display:
```
CPU: 65.3°C | 23.4%
GPU: 52.0°C | 45.2%
```

Values show "N/A" when unavailable (e.g., GPU temperature on non-NVIDIA systems).

### Controls

- **Left-click and drag** anywhere on the window to move it
- **Right-click** to open the context menu and exit
- The window is borderless and stays on top of other windows

## Architecture

The project is organized into clean, modular components:

- **`monitor.py`** - Main GUI application (tkinter)
- **`sensors.py`** - Unified sensor backend
- **`pdh_counters.py`** - Windows PDH API wrapper (ctypes)
- **`nvapi.py`** - NVIDIA GPU API wrapper (ctypes)

All system APIs are accessed through `ctypes` - no compiled extensions or external libraries.

## Technical Details

### CPU Metrics
- **Temperature**: Read from Windows Thermal Zone Information via PDH
- **Usage**: Read from Processor Performance counters via PDH

### GPU Metrics
- **Temperature**: 
  - NVIDIA: Direct NVAPI calls via ctypes (primary method)
  - Fallback: PDH counters (rarely available)
- **Usage**: Windows GPU Engine Performance counters via PDH

### Limitations

- **Windows only** - uses Windows-specific APIs
- **GPU temperature** may not be available on all systems:
  - Works reliably on NVIDIA GPUs with standard drivers
  - AMD/Intel integrated GPUs may show "N/A" for temperature
  - GPU usage should work on all modern GPUs
- **Requires administrator rights** on some systems for certain counters

## Development

Optional development dependencies for linting/type checking:

```bash
pip install -e ".[dev]"
```

Run type checking:
```bash
mypy *.py
```

Run linting:
```bash
ruff check .
```

## License

MIT License - feel free to use and modify as needed.

## Why No Dependencies?

This project demonstrates that sophisticated system monitoring can be achieved using only Python's standard library. By using `ctypes` to interface directly with Windows APIs, we avoid heavyweight dependencies while maintaining full functionality.

