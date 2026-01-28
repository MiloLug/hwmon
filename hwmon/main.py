from __future__ import annotations

import sys
from dataclasses import replace

from hwmon.components import (
    BaseComponent, CPUComponent, GPUComponent, LoadTempGraphComponent, NetworkComponent,
)
from hwmon.network import NetworkBackend
from hwmon.sensors import SensorBackend
from hwmon.window import OverlayWindow


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
        
        self._cpu = CPUComponent(container, replace(graph_style, graph_color="#4a9eff"))
        self._gpu = GPUComponent(container, replace(graph_style, graph_color="#4aff9e"))
        self._network = NetworkComponent(container, NetworkComponent.Style(width=self.WIDTH, sample_window=update_measures))
        
        self._components: list[BaseComponent] = [self._cpu, self._gpu, self._network]
        
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

    def _exit(self) -> None:
        """Clean up and exit the application."""
        self._exiting = True
        if self._after_id is not None:
            self._window.root.after_cancel(self._after_id)
        self._window.root.quit()

    def start(self) -> None:
        """Start the monitoring loop."""
        self._schedule_update()
        self._window.root.mainloop()

    def _schedule_update(self) -> None:
        self._update()
        self._after_id = self._window.root.after(self._refresh_ms, self._schedule_update)

    def _update(self) -> None:
        metrics = self._sensors.sample()
        net_metrics = self._network_backend.sample()
        
        self._cpu.add_sample(
            temp=metrics.get("cpu_temp"),
            usage=metrics.get("cpu_usage")
        )
        self._gpu.add_sample(
            temp=metrics.get("gpu_temp"),
            usage=metrics.get("gpu_usage")
        )
        self._network.add_sample(
            net_in=net_metrics.get("net_in"),
            net_out=net_metrics.get("net_out")
        )
        
        for component in self._components:
            component.update()


def main() -> None:
    """Entry point."""
    app = MonitorApp(refresh_ms=250, update_measures=4)
    app.start()


if __name__ == "__main__":
    main()
