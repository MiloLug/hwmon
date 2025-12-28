from __future__ import annotations

import sys
import tkinter as tk
from dataclasses import replace

from hwmon.components import (
    BaseComponent, CPUComponent, GPUComponent, LoadTempGraphComponent, NetworkComponent,
)
from hwmon.network import NetworkBackend
from hwmon.sensors import SensorBackend


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

        self._root = tk.Tk()
        self._root.title("HW Monitor")
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        
        self._drag_x = 0
        self._drag_y = 0
        self._after_id: str | None = None
        self._exiting = False

        container = tk.Frame(
            self._root,
            bg=self.BG_COLOR,
            highlightbackground=self.BORDER_COLOR,
            highlightthickness=1,
        )
        container.pack(fill="both", expand=True)

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
        self._bind_drag_events(self._root)
        self._bind_drag_events(container)
        for component in self._components:
            for widget in component.get_widgets():
                self._bind_drag_events(widget)
        
        self._create_context_menu()
    
    def _bind_drag_events(self, widget: tk.Misc) -> None:
        """Bind mouse drag events to a widget."""
        widget.bind("<Button-1>", self._start_drag)
        widget.bind("<B1-Motion>", self._on_drag)
    
    def _start_drag(self, event: tk.Event) -> None:
        """Record starting position for drag."""
        self._drag_x = event.x
        self._drag_y = event.y
    
    def _on_drag(self, event: tk.Event) -> None:
        """Handle window dragging."""
        x = self._root.winfo_x() + event.x - self._drag_x
        y = self._root.winfo_y() + event.y - self._drag_y
        self._root.geometry(f"+{x}+{y}")
    
    def _create_context_menu(self) -> None:
        """Create right-click context menu."""
        self._menu = tk.Menu(self._root, tearoff=0)
        self._menu.add_command(
            label="Exit", 
            command=lambda: self._root.after(1, self._exit),
        )
        def show_menu(event: tk.Event) -> None:
            self._menu.tk_popup(event.x_root, event.y_root)
        
        self._root.bind("<Button-3>", show_menu)

    def _exit(self) -> None:
        """Clean up and exit the application."""
        self._exiting = True
        if self._after_id is not None:
            self._root.after_cancel(self._after_id)
        self._root.quit()

    def start(self) -> None:
        """Start the monitoring loop."""
        self._schedule_update()
        self._root.mainloop()

    def _schedule_update(self) -> None:
        self._update()
        self._after_id = self._root.after(self._refresh_ms, self._schedule_update)

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
