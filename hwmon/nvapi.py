"""NVIDIA GPU monitoring via NVAPI using only ctypes (no external dependencies)."""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes


NVAPI_MAX_PHYSICAL_GPUS = 64
NVAPI_MAX_THERMAL_SENSORS_PER_GPU = 3


class NV_THERMAL_SENSOR(ctypes.Structure):
    _fields_ = [
        ('controller', wintypes.DWORD),
        ('defaultMinTemp', wintypes.DWORD),
        ('defaultMaxTemp', wintypes.DWORD),
        ('currentTemp', wintypes.DWORD),
        ('target', wintypes.DWORD),
    ]


class NV_GPU_THERMAL_SETTINGS(ctypes.Structure):
    _fields_ = [
        ('version', wintypes.DWORD),
        ('count', wintypes.DWORD),
        ('sensor', NV_THERMAL_SENSOR * NVAPI_MAX_THERMAL_SENSORS_PER_GPU),
    ]


class NVAPIGPUMonitor:
    """Reads NVIDIA GPU temperatures using NVAPI."""
    
    def __init__(self) -> None:
        self._gpu_handles = None
        self._gpu_count = 0
        self._nvapi_available = False
        self._get_thermal = None
        
        try:
            nvapi = ctypes.CDLL("nvapi64.dll")
            query_interface = nvapi.nvapi_QueryInterface
            query_interface.restype = ctypes.c_void_p
            query_interface.argtypes = [ctypes.c_uint32]
            
            # Get function pointers
            init_ptr = query_interface(0x0150E828)
            enum_ptr = query_interface(0xE5AC921F)
            thermal_ptr = query_interface(0xE3640A56)
            
            # Create callable functions
            nvapi_init = ctypes.CFUNCTYPE(ctypes.c_int)(init_ptr)
            nvapi_enum = ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.POINTER(ctypes.c_void_p * NVAPI_MAX_PHYSICAL_GPUS),
                ctypes.POINTER(wintypes.DWORD)
            )(enum_ptr)
            self._get_thermal = ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_void_p,
                ctypes.c_int,
                ctypes.POINTER(NV_GPU_THERMAL_SETTINGS)
            )(thermal_ptr)
            
            # Initialize and enumerate
            if nvapi_init() == 0:
                gpu_handles = (ctypes.c_void_p * NVAPI_MAX_PHYSICAL_GPUS)()
                gpu_count = wintypes.DWORD()
                if nvapi_enum(ctypes.byref(gpu_handles), ctypes.byref(gpu_count)) == 0:
                    self._gpu_handles = gpu_handles
                    self._gpu_count = gpu_count.value
                    self._nvapi_available = True
        except Exception:
            pass
    
    def get_temperatures(self) -> list[float]:
        """Returns list of GPU temperatures in Celsius."""
        if not self._nvapi_available or self._gpu_count == 0:
            return []
        
        temps = []
        for i in range(self._gpu_count):
            thermal = NV_GPU_THERMAL_SETTINGS()
            thermal.version = (ctypes.sizeof(NV_GPU_THERMAL_SETTINGS) | (1 << 16))
            
            status = self._get_thermal(
                self._gpu_handles[i],
                0,  # NVAPI_THERMAL_TARGET_ALL
                ctypes.byref(thermal)
            )
            
            if status == 0 and thermal.count > 0:
                temps.append(float(thermal.sensor[0].currentTemp))
        
        return temps
    
    @property
    def available(self) -> bool:
        """Check if NVAPI is available."""
        return self._nvapi_available
    
    @property
    def gpu_count(self) -> int:
        """Get number of GPUs detected."""
        return self._gpu_count

