from __future__ import annotations

import sys
from dataclasses import replace

from hwmon.components import (
    BaseComponent,
    CPUComponent,
    GPUComponent,
    LoadTempGraphComponent,
    # NetworkComponent,
    TimeComponent,
)
from hwmon.network import NetworkBackend
from hwmon.sensors import SensorBackend
from hwmon.window import OverlayWindow, SnapTarget


class MonitorApp:
    """Minimalistic hardware monitor GUI."""
    
    BG_COLOR = "#1e1e1e"
    BORDER_COLOR = "#3c3c3c"

    WIDTH = 80

    def __init__(self, refresh_ms: int = 1000, update_measures: int = 5) -> None:
        if sys.platform != "win32":
            raise SystemExit("This monitor currently supports Windows platforms only.")

        self._sensors = SensorBackend()
        self._network_backend = NetworkBackend()
        self._refresh_ms = refresh_ms

        self._window = OverlayWindow(
            title="HW Monitor",
            style=OverlayWindow.Style(
                bg_color=self.BG_COLOR,
                border_color=self.BORDER_COLOR,
            ),
        )
        self._after_id: str | None = None
        self._exiting = False
        container = self._window.container

        # Create components with shared style base
        graph_style = LoadTempGraphComponent.Style(
            width=self.WIDTH,
            sample_window=update_measures,
            temp_threshold=80.0,
        )
        
        self._time = TimeComponent(container, TimeComponent.Style(width=self.WIDTH, bg_color="#2a2a2a", font=("Segoe UI", 10)))
        self._cpu = CPUComponent(container, replace(graph_style, graph_color="#4a9eff"))
        self._gpu = GPUComponent(container, replace(graph_style, graph_color="#4aff9e"))
        #self._network = NetworkComponent(container, NetworkComponent.Style(width=self.WIDTH, sample_window=update_measures))
        
        self._components: list[BaseComponent] = [self._cpu, self._gpu, self._time]
        
        # Pack components
        for component in self._components:
            component.pack(fill="x")
        
        # Bind drag events
        widgets = [self._window.root, container]
        for component in self._components:
            widgets.extend(component.get_widgets())
        self._window.bind_drag_many(widgets)

        self._window.set_exit_callback(self._exit)
        self._window.install_context_menu()
        self._window.root.bind("<<WindowSnapChanged>>", self._on_snap_changed)

        self._minimized = False
        self._restore_size: tuple[int, int] | None = None
        for widget in self._time.get_widgets():
            widget.bind("<ButtonRelease-1>", self._on_time_release, add="+")
        self._window.container.bind(
            "<ButtonRelease-1>", self._on_container_release, add="+"
        )

    def _exit(self) -> None:
        """Clean up and exit the application."""
        self._exiting = True
        if self._after_id is not None:
            self._window.root.after_cancel(self._after_id)
        self._window.root.quit()

    def _on_snap_changed(self, _event) -> None:
        is_top = self._window.snap_target in {
            SnapTarget.TOP,
            SnapTarget.TOPLEFT,
            SnapTarget.TOPRIGHT,
        }
        if not is_top and self._minimized:
            self._restore_from_strip()

    def start(self) -> None:
        """Start the monitoring loop."""
        self._schedule_update()
        self._window.root.mainloop()

    def _schedule_update(self) -> None:
        self._update()
        self._after_id = self._window.root.after(self._refresh_ms, self._schedule_update)

    def _update(self) -> None:
        metrics = self._sensors.sample()
        # net_metrics = self._network_backend.sample()
        
        self._cpu.add_sample(
            temp=metrics.get("cpu_temp"),
            usage=metrics.get("cpu_usage")
        )
        self._gpu.add_sample(
            temp=metrics.get("gpu_temp"),
            usage=metrics.get("gpu_usage")
        )
        # self._network.add_sample(
        #     net_in=net_metrics.get("net_in"),
        #     net_out=net_metrics.get("net_out")
        # )
        
        for component in self._components:
            component.update()

    def _on_time_release(self, _event) -> None:
        if self._window.snap_target not in {
            SnapTarget.TOP,
            SnapTarget.TOPLEFT,
            SnapTarget.TOPRIGHT,
        }:
            return
        if self._window.was_click():
            self._toggle_minimized()

    def _on_container_release(self, _event) -> None:
        if not self._minimized:
            return
        if self._window.was_click():
            self._restore_from_strip()

    def _toggle_minimized(self) -> None:
        if self._minimized:
            self._restore_from_strip()
        else:
            self._minimize_to_strip()

    def _minimize_to_strip(self) -> None:
        self._window.root.update_idletasks()
        w = self._window.root.winfo_width()
        h = self._window.root.winfo_height()
        x = self._window.root.winfo_x()
        y = self._window.root.winfo_y()
        self._restore_size = (w, h)

        for component in self._components:
            if component is self._time:
                component.show()
            else:
                component.hide()
        self._window.root.update_idletasks()
        time_frame = self._time.get_widgets()[0]
        time_h = max(time_frame.winfo_reqheight(), time_frame.winfo_height(), 1)
        self._window.root.geometry(f"{w}x{time_h}+{x}+{y}")
        self._minimized = True

    def _restore_from_strip(self) -> None:
        for component in self._components:
            component.hide()
        for component in self._components:
            component.show()
        if self._restore_size is not None:
            w, h = self._restore_size
            x = self._window.root.winfo_x()
            y = self._window.root.winfo_y()
            self._window.root.geometry(f"{w}x{h}+{x}+{y}")
        self._minimized = False

def main() -> None:
    """Entry point."""
    app = MonitorApp(refresh_ms=250, update_measures=4)
    app.start()


if __name__ == "__main__":
    main()
