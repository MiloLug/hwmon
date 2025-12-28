import time

from hwmon.amdadl import ADLGPUInitError, ADLGPUMonitor
from hwmon.nvapi import NVAPIInitError, NVAPIGPUMonitor
from hwmon.pdh_counters import PDHQuery

import logging

logger = logging.getLogger(__name__)

def to_celsius(raw: float) -> float:
    """Convert temperature to Celsius, handling Kelvin thermal zones."""
    if raw > 200:  # PDH thermal counters report Kelvin
        return raw - 273.15
    return raw


class SensorBackend:
    """Unified backend for reading CPU and GPU sensors."""
    
    def __init__(self) -> None:
        self._query = PDHQuery()
        self._query.add_counter("cpu_temp", r"\Thermal Zone Information(*)\Temperature")
        self._query.add_counter("cpu_usage", r"\Processor(_Total)\% Processor Time")
        self._query.add_counter("gpu_temp", r"\GPU Adapter(*)\Temperature")

        self._query.add_counter("gpu_usage", r"\GPU Engine(*)\Utilization Percentage")
        self._gpu_usage_names = set[str]()
        
        self._nvapi: NVAPIGPUMonitor | None = None
        self._amdadl: ADLGPUMonitor | None = None

        try:
            self._nvapi = NVAPIGPUMonitor()
        except NVAPIInitError:
            logger.warning("Failed to initialize NVAPI")

        try:
            self._amdadl = ADLGPUMonitor()
        except ADLGPUInitError:
            logger.warning("Failed to initialize ADL")

        if self._query.collect():
            time.sleep(0.2)
            self._query.collect()

    def sample(self) -> dict[str, float | None]:
        """Collect current sensor readings."""
        self._query.collect()
        return {
            "cpu_temp": self._cpu_temperature(),
            "cpu_usage": self._get_cpu_usage(),
            "gpu_temp": self._gpu_temperature(),
            "gpu_usage": self._gpu_usage(),
        }

    def _get_cpu_usage(self) -> float | None:
        value = self._query.get_value("cpu_usage")
        if value is None:
            return None
        return max(0.0, min(value, 100.0))

    def _cpu_temperature(self) -> float | None:
        readings = self._query.get_dict("cpu_temp")
        temps = []
        for name, value in readings.items():
            if value:
                temps.append((name, to_celsius(value)))
        if not temps:
            return None
        for name, value in temps:
            if "cpu" in name:
                return value
        return sum(val for _, val in temps) / len(temps)

    def _gpu_usage(self) -> float | None:
        readings = self._query.get_dict("gpu_usage")
        values = []
        if not self._gpu_usage_names:
            for name, value in readings.items():
                if value is None:
                    continue
                if "engtype_3d" in name or "engtype_compute" in name or "engtype_copy" in name or "_total" in name:
                    values.append(value)
                    self._gpu_usage_names.add(name)
        else:
            for name in self._gpu_usage_names:
                if (value := readings.get(name)) is not None:
                    values.append(value)
        if not values:
            return None
        total = sum(values)
        return max(0.0, min(total, 100.0))

    def _gpu_temp_nvidia(self) -> float | None:
        """Get GPU temperature from NVIDIA NVAPI."""
        if self._nvapi is None:
            return None
        nvapi_temps = self._nvapi.get_temperatures()
        if nvapi_temps:
            return sum(nvapi_temps) / len(nvapi_temps)
        return None
    
    def _gpu_temp_amd(self) -> float | None:
        """Get GPU temperature from AMD ADL."""
        if self._amdadl is None:
            return None
        amd_temps = self._amdadl.get_temperatures()
        if amd_temps:
            return sum(amd_temps) / len(amd_temps)
        return None
    
    def _gpu_temp_pdh(self) -> float | None:
        """Get GPU temperature from PDH GPU Adapter counter."""
        readings = self._query.get_array("gpu_temp")
        temps = [to_celsius(value) for value in readings if value is not None]
        if temps:
            return sum(temps) / len(temps)
        return None
    
    def _gpu_temperature(self) -> float | None:
        """Get GPU temperature from available sources."""
        # Try NVAPI first (NVIDIA GPUs)
        temp = self._gpu_temp_nvidia()
        if temp is not None:
            return temp
        
        # Try AMD ADL (AMD discrete and some integrated GPUs)
        temp = self._gpu_temp_amd()
        if temp is not None:
            return temp
        
        # Try PDH GPU Adapter counter
        temp = self._gpu_temp_pdh()
        if temp is not None:
            return temp
        
        return None