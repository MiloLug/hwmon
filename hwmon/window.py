from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import tkinter as tk
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable, NamedTuple


SNAP_PX = 16


class SnapTarget(StrEnum):
    NONE = "none"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    TOPLEFT = "topleft"
    TOPRIGHT = "topright"
    BOTTOMLEFT = "bottomleft"
    BOTTOMRIGHT = "bottomright"


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
    ]


class Monitor(NamedTuple):
    monitor_rect: tuple[int, int, int, int]
    work_rect: tuple[int, int, int, int]


user32 = ctypes.windll.user32
MONITORENUMPROC = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HMONITOR,
    wintypes.HDC,
    ctypes.POINTER(RECT),
    wintypes.LPARAM,
)
user32.EnumDisplayMonitors.argtypes = [
    wintypes.HDC,
    ctypes.POINTER(RECT),
    MONITORENUMPROC,
    wintypes.LPARAM,
]
user32.EnumDisplayMonitors.restype = wintypes.BOOL
user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFO)]
user32.GetMonitorInfoW.restype = wintypes.BOOL


def _contains_point(left: int, top: int, right: int, bottom: int, px: int, py: int) -> bool:
    return left <= px <= right and top <= py <= bottom


def _dist2_to_rect(left: int, top: int, right: int, bottom: int, px: int, py: int) -> int:
    cx = min(max(px, left), right)
    cy = min(max(py, top), bottom)
    dx = px - cx
    dy = py - cy
    return dx * dx + dy * dy


class OverlayWindow:
    """Borderless, draggable overlay window with a content container."""

    @dataclass
    class Style:
        bg_color: str
        border_color: str
        border_thickness: int = 1
        topmost: bool = True
        borderless: bool = True

    def __init__(self, title: str, style: Style) -> None:
        self.root = tk.Tk()
        self.root.title(title)
        if style.borderless:
            self.root.overrideredirect(True)
        if style.topmost:
            self.root.attributes("-topmost", True)

        self.container = tk.Frame(
            self.root,
            bg=style.bg_color,
            highlightbackground=style.border_color,
            highlightthickness=style.border_thickness,
        )
        self.container.pack(fill="both", expand=True)

        self._drag_off_x = 0
        self._drag_off_y = 0
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._monitors: list[Monitor] = []
        self._snap_target = SnapTarget.NONE
        self._last_released_snap_target = SnapTarget.NONE
        self._exit_callback: Callable[[], None] | None = None
        self._menu: tk.Menu | None = None

    def bind_drag(self, widget: tk.Misc) -> None:
        """Bind mouse drag events to a widget."""
        widget.bind("<Button-1>", self._start_drag)
        widget.bind("<B1-Motion>", self._on_drag)
        widget.bind("<ButtonRelease-1>", self._on_release)

    def bind_drag_many(self, widgets: list[tk.Misc]) -> None:
        """Bind mouse drag events to multiple widgets."""
        for widget in widgets:
            self.bind_drag(widget)

    def set_exit_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback invoked by the context menu exit action."""
        self._exit_callback = callback

    def install_context_menu(self) -> None:
        """Create and bind a right-click context menu."""
        self._menu = tk.Menu(self.root, tearoff=0)
        self._menu.add_command(label="Exit", command=self._on_exit_menu)

        def show_menu(event: tk.Event) -> None:
            if self._menu is not None:
                self._menu.tk_popup(event.x_root, event.y_root)

        self.root.bind("<Button-3>", show_menu)

    def _start_drag(self, event: tk.Event) -> None:
        """Record starting position for drag."""
        self._drag_off_x = event.x_root - self.root.winfo_x()
        self._drag_off_y = event.y_root - self.root.winfo_y()
        self._drag_start_x = self.root.winfo_x()
        self._drag_start_y = self.root.winfo_y()
        self._refresh_monitor_cache()

    def _on_drag(self, event: tk.Event) -> None:
        """Handle window dragging."""
        x = event.x_root - self._drag_off_x
        y = event.y_root - self._drag_off_y
        w = self.root.winfo_width()
        h = self.root.winfo_height()

        monitor = self._pick_monitor(event.x_root, event.y_root)
        if monitor is not None:
            x, y, target = self._apply_snap(x, y, w, h, monitor.work_rect)
            self._snap_target = target
        else:
            self._snap_target = SnapTarget.NONE

        self.root.geometry(f"+{x}+{y}")

    def _on_release(self, event: tk.Event) -> None:
        monitor = self._pick_monitor(event.x_root, event.y_root)
        if monitor is None:
            target = SnapTarget.NONE
        else:
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            x = self.root.winfo_x()
            y = self.root.winfo_y()
            _, _, target = self._apply_snap(x, y, w, h, monitor.work_rect)

        self._snap_target = target
        if target != self._last_released_snap_target:
            self._last_released_snap_target = target
            self.root.event_generate("<<WindowSnapChanged>>")

    def _on_exit_menu(self) -> None:
        if self._exit_callback is not None:
            self.root.after(1, self._exit_callback)

    def _refresh_monitor_cache(self) -> None:
        monitors: list[Monitor] = []

        def enum_proc(hmon, _hdc, _lprect, _lparam) -> int:
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                mr = mi.rcMonitor
                wr = mi.rcWork
                monitors.append(
                    Monitor(
                        monitor_rect=(mr.left, mr.top, mr.right, mr.bottom),
                        work_rect=(wr.left, wr.top, wr.right, wr.bottom),
                    )
                )
            return 1

        enum_cb = MONITORENUMPROC(enum_proc)
        if not user32.EnumDisplayMonitors(0, None, enum_cb, 0):
            monitors = []

        if not monitors:
            width = self.root.winfo_screenwidth()
            height = self.root.winfo_screenheight()
            monitors = [Monitor(monitor_rect=(0, 0, width, height), work_rect=(0, 0, width, height))]

        self._monitors = monitors

    def _pick_monitor(self, px: int, py: int) -> Monitor | None:
        if not self._monitors:
            return None

        contained: list[Monitor] = []
        for monitor in self._monitors:
            left, top, right, bottom = monitor.monitor_rect
            if _contains_point(left, top, right, bottom, px, py):
                contained.append(monitor)

        candidates = contained if contained else self._monitors
        best = candidates[0]
        best_dist = _dist2_to_rect(*best.monitor_rect, px, py)
        for monitor in candidates[1:]:
            dist = _dist2_to_rect(*monitor.monitor_rect, px, py)
            if dist < best_dist:
                best = monitor
                best_dist = dist
        return best

    def _apply_snap(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        work_rect: tuple[int, int, int, int],
    ) -> tuple[int, int, SnapTarget]:
        left, top, right, bottom = work_rect
        dl = abs(x - left)
        dr = abs((x + w) - right)
        dt = abs(y - top)
        db = abs((y + h) - bottom)

        snap_x: SnapTarget | None = None
        snap_y: SnapTarget | None = None

        if dl <= SNAP_PX and dl <= dr:
            x = left
            snap_x = SnapTarget.LEFT
        elif dr <= SNAP_PX:
            x = right - w
            snap_x = SnapTarget.RIGHT

        if dt <= SNAP_PX and dt <= db:
            y = top
            snap_y = SnapTarget.TOP
        elif db <= SNAP_PX:
            y = bottom - h
            snap_y = SnapTarget.BOTTOM

        if snap_x and snap_y:
            if snap_y == SnapTarget.TOP and snap_x == SnapTarget.LEFT:
                target = SnapTarget.TOPLEFT
            elif snap_y == SnapTarget.TOP and snap_x == SnapTarget.RIGHT:
                target = SnapTarget.TOPRIGHT
            elif snap_y == SnapTarget.BOTTOM and snap_x == SnapTarget.LEFT:
                target = SnapTarget.BOTTOMLEFT
            else:
                target = SnapTarget.BOTTOMRIGHT
        elif snap_x:
            target = snap_x
        elif snap_y:
            target = snap_y
        else:
            target = SnapTarget.NONE

        return x, y, target

    @property
    def snap_target(self) -> SnapTarget:
        return self._snap_target

    def was_click(self, threshold: int = 3) -> bool:
        """Return True if the last drag moved less than threshold pixels."""
        return (
            abs(self.root.winfo_x() - self._drag_start_x) < threshold
            and abs(self.root.winfo_y() - self._drag_start_y) < threshold
        )
