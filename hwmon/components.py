"""Reusable UI components for the hardware monitor."""

from __future__ import annotations

import tkinter as tk
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass

from hwmon.utils import mean


class BaseComponent(ABC):
    """Base class for monitor UI components."""
    
    @dataclass
    class Style:
        """Base style for all components."""
        color: str | None = None
        width: int | None = None
    
    BG_COLOR = "#1e1e1e"
    TEXT_COLOR = "#e0e0e0"
    TEXT_COLOR_DIM = "#888888"
    FONT = ("Segoe UI", 11)
    
    def __init__(self, parent: tk.Widget, style: Style) -> None:
        self._parent = parent
        self._color = style.color or self.TEXT_COLOR
        self._width = style.width
        
        self._frame = tk.Frame(parent, bg=self.BG_COLOR, width=style.width or 0)
        self._widgets: list[tk.Widget] = [self._frame]
        
        self._build_ui()
    
    @abstractmethod
    def _build_ui(self) -> None:
        """Build the component UI (labels and visualization)."""
        pass
    
    @abstractmethod
    def _update(self) -> None:
        """Update the component display."""
        pass

    @abstractmethod
    def update(self) -> bool:
        """Update the component. Returns True if display was refreshed."""
        pass
    
    def pack(self, **kwargs) -> None:
        """Pack the component frame."""
        self._frame.pack(**kwargs)
    
    def get_widgets(self) -> list[tk.Widget]:
        """Return all widgets for event binding."""
        return self._widgets


class SampledComponent(BaseComponent):
    """Component with sample averaging and history tracking."""
    
    @dataclass
    class Style(BaseComponent.Style):
        """Style for sampled components."""
        history_len: int = 60
        sample_window: int = 4
    
    def __init__(self, parent: tk.Widget, label_text: str, style: Style) -> None:
        self._label_text = label_text
        self._history: deque[float] = deque([0.0] * style.history_len, maxlen=style.history_len)
        self._samples: deque[float] = deque([0.0], maxlen=style.sample_window)
        self._sample_window = style.sample_window
        self._sample_count = 0
        super().__init__(parent, style)
    
    def add_sample(self, value: float | None) -> None:
        """Add a new sample value."""
        if value is not None:
            self._samples.append(value)
    
    def update(self) -> bool:
        """Update the component. Returns True if display was refreshed."""
        self._sample_count += 1
        if self._sample_count >= self._sample_window:
            self._sample_count = 0
            avg = mean(self._samples)
            self._history.append(avg)
            self._update()
            return True
        return False


class GraphComponent(SampledComponent):
    """Generic component with a line graph visualization."""
    
    @dataclass
    class Style(SampledComponent.Style):
        """Style for graph components."""
        max_value: float = 100.0
        graph_color: str | None = None
    
    GRAPH_HEIGHT = 20
    GRAPH_BG = "#2a2a2a"
    
    def __init__(self, parent: tk.Widget, label_text: str, style: Style) -> None:
        self._max_value = style.max_value
        self._graph_color = style.graph_color or self.TEXT_COLOR
        super().__init__(parent, label_text, style)
    
    def _build_ui(self) -> None:
        self._build_canvas()
    
    def _build_canvas(self) -> None:
        # Graph canvas
        canvas_width = self._width - 20 if self._width else 0
        self._canvas = tk.Canvas(
            self._frame,
            width=canvas_width,
            height=self.GRAPH_HEIGHT,
            bg=self.GRAPH_BG,
            highlightthickness=0,
        )
        self._canvas.pack(fill="x", padx=10, pady=(0, 5))
        self._widgets.append(self._canvas)
    
    def _update(self) -> None:
        self._draw_graph()
    
    def _draw_graph(self) -> None:
        history = list(self._history)
        if len(history) < 2:
            return
        
        width = self._canvas.winfo_width()
        height = self._canvas.winfo_height()
        if not (width and height):
            return
        
        self._canvas.delete("all")
        
        # Draw center line
        self._canvas.create_line(
            0, height // 2, width, height // 2,
            fill="#3a3a3a", width=1
        )
        
        n = len(history)
        x_coords = [i * width / (n - 1) for i in range(n)]
        hist_max = max(max(history), self._max_value)
        y_coords = [(1 - val / hist_max) * height for val in history]
        
        points = list(zip(x_coords, y_coords))
        self._canvas.create_line(points, fill=self._graph_color, width=2, smooth=True)


class LoadTempGraphComponent(GraphComponent):
    """Graph component with temperature and usage display."""
    
    @dataclass
    class Style(GraphComponent.Style):
        """Style for load/temp graph components."""
        temp_threshold: float | None = None
    
    WARN_COLOR = "#ff4444"
    
    def __init__(self, parent: tk.Widget, label_text: str, style: Style) -> None:
        self._temp_threshold = style.temp_threshold
        self._usage_samples: deque[float] = deque([0.0], maxlen=style.sample_window)
        super().__init__(parent, label_text, style)
    
    def _build_ui(self) -> None:
        # Label row
        label_row = tk.Frame(self._frame, bg=self.BG_COLOR)
        label_row.pack(fill="x", padx=10)
        
        self._name_label = tk.Label(
            label_row,
            text=f"{self._label_text}:",
            font=self.FONT,
            bg=self.BG_COLOR,
            fg=self._color,
            anchor="w",
        )
        self._name_label.pack(side="left")
        
        # Right side container for temp and usage
        right_frame = tk.Frame(label_row, bg=self.BG_COLOR)
        right_frame.pack(side="right")
        
        self._temp_label = tk.Label(
            right_frame,
            text="--",
            font=self.FONT,
            bg=self.BG_COLOR,
            fg=self._color,
            anchor="e",
            width=7,
        )
        self._temp_label.pack(side="left")
        
        self._usage_label = tk.Label(
            right_frame,
            text="--",
            font=self.FONT,
            bg=self.BG_COLOR,
            fg=self._color,
            anchor="e",
            width=6,
        )
        self._usage_label.pack(side="left")
        
        self._widgets.extend([
            label_row, self._name_label, right_frame,
            self._temp_label, self._usage_label
        ])
        
        # Graph canvas
        self._build_canvas()
    
    def _update(self) -> None:
        temp = self._history[-1] if self._history else None
        usage = mean(self._usage_samples)
        
        temp_txt = f"{temp:.1f}°C" if temp is not None else "N/A"
        usage_txt = f"{usage:.1f}%" if usage is not None else "N/A"
        
        self._temp_label.configure(text=temp_txt)
        self._usage_label.configure(text=usage_txt)
        self._draw_graph()
    
    def _draw_graph(self) -> None:
        history = list(self._history)
        if len(history) < 2:
            return
        
        width = self._canvas.winfo_width()
        height = self._canvas.winfo_height()
        if not (width and height):
            return
        
        self._canvas.delete("all")
        
        # Draw center line
        self._canvas.create_line(
            0, height // 2, width, height // 2,
            fill="#3a3a3a", width=1
        )
        
        n = len(history)
        x_coords = [i * width / (n - 1) for i in range(n)]
        hist_max = max(max(history), self._max_value)
        y_coords = [(1 - val / hist_max) * height for val in history]
        
        # Use warn color if temp exceeds threshold
        temp = self._history[-1] if self._history else None
        if self._temp_threshold and temp and temp > self._temp_threshold:
            graph_color = self.WARN_COLOR
        else:
            graph_color = self._graph_color
        
        points = list(zip(x_coords, y_coords))
        self._canvas.create_line(points, fill=graph_color, width=2, smooth=True)
    
    def add_sample(self, temp: float | None = None, usage: float | None = None) -> None:
        """Add temperature and usage samples."""
        if temp is not None:
            self._samples.append(temp)
        if usage is not None:
            self._usage_samples.append(usage)


class NetworkComponent(BaseComponent):
    """Component showing network in/out on a single row with arrows."""
    
    @dataclass
    class Style(BaseComponent.Style):
        """Style for network component."""
        sample_window: int = 4
    
    DOWN_COLOR = "#8b5cf6"  # Purple for download
    UP_COLOR = "#eab308"    # Yellow for upload
    
    def __init__(self, parent: tk.Widget, style: Style | None = None) -> None:
        style = style or NetworkComponent.Style()
        self._sample_window = style.sample_window
        self._in_samples: deque[float] = deque([0.0], maxlen=style.sample_window)
        self._out_samples: deque[float] = deque([0.0], maxlen=style.sample_window)
        self._sample_count = 0
        self._current_in: float = 0.0
        self._current_out: float = 0.0
        super().__init__(parent, style)
    
    def _build_ui(self) -> None:
        row = tk.Frame(self._frame, bg=self.BG_COLOR)
        row.pack(fill="x", padx=10, pady=2)
        
        # Down arrow and value
        self._down_label = tk.Label(
            row,
            text="↓ --",
            font=self.FONT,
            bg=self.BG_COLOR,
            fg=self.DOWN_COLOR,
            anchor="w",
        )
        self._down_label.pack(side="left")
        
        # Up arrow and value
        self._up_label = tk.Label(
            row,
            text="↑ --",
            font=self.FONT,
            bg=self.BG_COLOR,
            fg=self.UP_COLOR,
            anchor="e",
        )
        self._up_label.pack(side="right")
        
        self._widgets.extend([row, self._down_label, self._up_label])
    
    def _update(self) -> None:
        self._down_label.configure(text=f"↓ {_format_speed(self._current_in)}")
        self._up_label.configure(text=f"↑ {_format_speed(self._current_out)}")
    
    def add_sample(self, net_in: float | None = None, net_out: float | None = None) -> None:
        """Add network in/out samples."""
        if net_in is not None:
            self._in_samples.append(net_in)
        if net_out is not None:
            self._out_samples.append(net_out)
    
    def update(self) -> bool:
        """Update the component. Returns True if display was refreshed."""
        self._sample_count += 1
        if self._sample_count >= self._sample_window:
            self._sample_count = 0
            self._current_in = mean(self._in_samples)
            self._current_out = mean(self._out_samples)
            self._update()
            return True
        return False


class CPUComponent(LoadTempGraphComponent):
    """CPU temperature and usage component."""
    
    DEFAULT_STYLE = LoadTempGraphComponent.Style(graph_color="#4a9eff")
    
    def __init__(self, parent: tk.Widget, style: LoadTempGraphComponent.Style | None = None) -> None:
        style = style or self.DEFAULT_STYLE
        super().__init__(parent, "CPU", style)


class GPUComponent(LoadTempGraphComponent):
    """GPU temperature and usage component."""
    
    DEFAULT_STYLE = LoadTempGraphComponent.Style(graph_color="#4aff9e")
    
    def __init__(self, parent: tk.Widget, style: LoadTempGraphComponent.Style | None = None) -> None:
        style = style or self.DEFAULT_STYLE
        super().__init__(parent, "GPU", style)


def _format_speed(bytes_per_sec: float | None) -> str:
    """Format bytes per second as human-readable string."""
    if bytes_per_sec is None:
        return "N/A"
    if bytes_per_sec >= 1024 * 1024:
        return f"{bytes_per_sec / (1024 * 1024):.1f} MB"
    elif bytes_per_sec >= 1024:
        return f"{bytes_per_sec / 1024:.1f} KB"
    return f"{int(bytes_per_sec)} B"
