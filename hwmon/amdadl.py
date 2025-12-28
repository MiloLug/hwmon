import ctypes


# ADL Constants
ADL_OK = 0
ADL_MAX_PATH = 256
ADL_MAX_ADAPTERS = 40
ADL_MAX_DISPLAYS = 40
ADL_MAX_DEVICENAME = 32


class ADLAdapterInfo(ctypes.Structure):
    """ADL adapter information structure."""
    _fields_ = [
        ('iSize', ctypes.c_int),
        ('iAdapterIndex', ctypes.c_int),
        ('strUDID', ctypes.c_char * ADL_MAX_PATH),
        ('iBusNumber', ctypes.c_int),
        ('iDeviceNumber', ctypes.c_int),
        ('iFunctionNumber', ctypes.c_int),
        ('iVendorID', ctypes.c_int),
        ('strAdapterName', ctypes.c_char * ADL_MAX_PATH),
        ('strDisplayName', ctypes.c_char * ADL_MAX_PATH),
        ('iPresent', ctypes.c_int),
        ('iExist', ctypes.c_int),
        ('strDriverPath', ctypes.c_char * ADL_MAX_PATH),
        ('strDriverPathExt', ctypes.c_char * ADL_MAX_PATH),
        ('strPNPString', ctypes.c_char * ADL_MAX_PATH),
        ('iOSDisplayIndex', ctypes.c_int),
    ]


class ADLTemperature(ctypes.Structure):
    """ADL temperature structure."""
    _fields_ = [
        ('iSize', ctypes.c_int),
        ('iTemperature', ctypes.c_int),  # Temperature in 1/1000 degrees Celsius
    ]


class ADLPMActivity(ctypes.Structure):
    """ADL Performance Metrics Activity structure."""
    _fields_ = [
        ('iSize', ctypes.c_int),
        ('iEngineClock', ctypes.c_int),
        ('iMemoryClock', ctypes.c_int),
        ('iVddc', ctypes.c_int),
        ('iActivityPercent', ctypes.c_int),
        ('iCurrentPerformanceLevel', ctypes.c_int),
        ('iCurrentBusSpeed', ctypes.c_int),
        ('iCurrentBusLanes', ctypes.c_int),
        ('iMaximumBusLanes', ctypes.c_int),
        ('iReserved', ctypes.c_int),
    ]


# Memory allocation callback for ADL
ADL_Main_Memory_Alloc = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_int)

@ADL_Main_Memory_Alloc
def adl_malloc(size: int) -> int | None:
    """Allocate memory for ADL."""
    return ctypes.cast(ctypes.create_string_buffer(size), ctypes.c_void_p).value


class ADLGPUInitError(Exception):
    """Error initializing ADL."""
    pass


# Tbh I can't test this, don't have any AMDs, so I just asked AI to write this part...

class ADLGPUMonitor:
    """Reads AMD GPU temperatures and metrics using ADL."""
    
    def __init__(self) -> None:
        self._adl_available = False
        self._adapter_count = 0
        self._adapter_indices: list[int] = []
        
        try:
            # Try to load 64-bit ADL library first
            try:
                adl = ctypes.CDLL("atiadlxx.dll")
            except OSError:
                # Fall back to 32-bit library
                adl = ctypes.CDLL("atiadlxy.dll")
            
            # Define function prototypes
            adl_main_control_create = adl.ADL_Main_Control_Create
            adl_main_control_create.argtypes = [ADL_Main_Memory_Alloc, ctypes.c_int]
            adl_main_control_create.restype = ctypes.c_int
            
            self._adl_main_control_destroy = adl.ADL_Main_Control_Destroy
            self._adl_main_control_destroy.restype = ctypes.c_int
            
            adl_adapter_numberofadapters_get = adl.ADL_Adapter_NumberOfAdapters_Get
            adl_adapter_numberofadapters_get.argtypes = [ctypes.POINTER(ctypes.c_int)]
            adl_adapter_numberofadapters_get.restype = ctypes.c_int
            
            adl_adapter_adapterinfo_get = adl.ADL_Adapter_AdapterInfo_Get
            adl_adapter_adapterinfo_get.argtypes = [ctypes.c_void_p, ctypes.c_int]
            adl_adapter_adapterinfo_get.restype = ctypes.c_int
            
            adl_adapter_active_get = adl.ADL_Adapter_Active_Get
            adl_adapter_active_get.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
            adl_adapter_active_get.restype = ctypes.c_int
            
            self._adl_overdrive5_temperature_get = adl.ADL_Overdrive5_Temperature_Get
            self._adl_overdrive5_temperature_get.argtypes = [
                ctypes.c_int,
                ctypes.c_int,
                ctypes.POINTER(ADLTemperature)
            ]
            self._adl_overdrive5_temperature_get.restype = ctypes.c_int
            
            self._adl_overdrive5_currentactivity_get = adl.ADL_Overdrive5_CurrentActivity_Get
            self._adl_overdrive5_currentactivity_get.argtypes = [
                ctypes.c_int,
                ctypes.POINTER(ADLPMActivity)
            ]
            self._adl_overdrive5_currentactivity_get.restype = ctypes.c_int
            
            # Initialize ADL
            if adl_main_control_create(adl_malloc, 1) != ADL_OK:
                return
            
            # Get number of adapters
            num_adapters = ctypes.c_int()
            if adl_adapter_numberofadapters_get(ctypes.byref(num_adapters)) != ADL_OK:
                return
            
            if num_adapters.value == 0:
                return
            
            # Get adapter info
            adapter_info_array = (ADLAdapterInfo * num_adapters.value)()
            adapter_buffer = ctypes.cast(adapter_info_array, ctypes.c_void_p)
            buffer_size = ctypes.sizeof(ADLAdapterInfo) * num_adapters.value
            
            if adl_adapter_adapterinfo_get(adapter_buffer, buffer_size) != ADL_OK:
                return
            
            # Find active adapters
            for i in range(num_adapters.value):
                adapter = adapter_info_array[i]
                if adapter.iPresent and adapter.iExist:
                    is_active = ctypes.c_int()
                    if adl_adapter_active_get(adapter.iAdapterIndex, ctypes.byref(is_active)) == ADL_OK:
                        if is_active.value:
                            self._adapter_indices.append(adapter.iAdapterIndex)
            
            if self._adapter_indices:
                self._adapter_count = len(self._adapter_indices)
                self._adl_available = True
                
        except Exception:
            raise ADLGPUInitError("Failed to initialize ADL")
    
    def get_temperatures(self) -> list[float]:
        """Returns list of GPU temperatures in Celsius."""
        if not self._adl_available or self._adapter_count == 0:
            return []
        
        temps = []
        for adapter_index in self._adapter_indices:
            temp = ADLTemperature()
            temp.iSize = ctypes.sizeof(ADLTemperature)
            
            # 0 = GPU core temperature
            status = self._adl_overdrive5_temperature_get(
                adapter_index,
                0,
                ctypes.byref(temp)
            )
            
            if status == ADL_OK:
                # Convert from millidegrees to degrees Celsius
                celsius = temp.iTemperature / 1000.0
                if 0 < celsius < 150:  # Sanity check
                    temps.append(celsius)
        
        return temps
    
    def get_activity(self) -> list[int]:
        """Returns list of GPU activity percentages."""
        if not self._adl_available or self._adapter_count == 0:
            return []
        
        activities = []
        for adapter_index in self._adapter_indices:
            activity = ADLPMActivity()
            activity.iSize = ctypes.sizeof(ADLPMActivity)
            
            status = self._adl_overdrive5_currentactivity_get(
                adapter_index,
                ctypes.byref(activity)
            )
            
            if status == ADL_OK:
                # Activity is already in percentage
                activities.append(activity.iActivityPercent)
        
        return activities
    
    @property
    def available(self) -> bool:
        """Check if ADL is available."""
        return self._adl_available
    
    @property
    def adapter_count(self) -> int:
        """Get number of adapters detected."""
        return self._adapter_count
    
    def __del__(self) -> None:
        """Cleanup ADL resources."""
        if self._adl_available and self._adl_main_control_destroy:
            try:
                self._adl_main_control_destroy()
            except Exception:
                pass

