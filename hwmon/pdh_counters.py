import ctypes
from ctypes import _Pointer
import ctypes.wintypes as wintypes


ERROR_SUCCESS = 0
PDH_FMT_DOUBLE = 0x00000200
PDH_MORE_DATA = 0x800007D2


class PDHError(RuntimeError):
    """Encapsulates PDH-related failures."""


def fmt_error(status: int) -> str:
    return ctypes.FormatError(status).strip()


class PDH_FMT_COUNTERVALUE_DOUBLE(ctypes.Structure):
    _fields_ = [
        ("CStatus", wintypes.DWORD),
        ("doubleValue", ctypes.c_double),
    ]


class PDH_FMT_COUNTERVALUE_ITEM_DOUBLE(ctypes.Structure):
    _fields_ = [
        ("szName", wintypes.LPWSTR),
        ("FmtValue", PDH_FMT_COUNTERVALUE_DOUBLE),
    ]


pdh = ctypes.windll.pdh


def _init_pdh_functions():
    PdhOpenQuery = pdh.PdhOpenQueryW
    PdhOpenQuery.argtypes = [wintypes.LPCWSTR, ctypes.c_void_p, ctypes.POINTER(wintypes.HANDLE)]
    PdhOpenQuery.restype = wintypes.DWORD

    try:
        PdhAddEnglishCounter = pdh.PdhAddEnglishCounterW
    except AttributeError:  # Fallback for older builds.
        PdhAddEnglishCounter = pdh.PdhAddCounterW
    PdhAddEnglishCounter.argtypes = [wintypes.HANDLE, wintypes.LPCWSTR, ctypes.c_ulonglong, ctypes.POINTER(wintypes.HANDLE)]
    PdhAddEnglishCounter.restype = wintypes.DWORD

    PdhCollectQueryData = pdh.PdhCollectQueryData
    PdhCollectQueryData.argtypes = [wintypes.HANDLE]
    PdhCollectQueryData.restype = wintypes.DWORD

    PdhGetFormattedCounterValue = pdh.PdhGetFormattedCounterValue
    PdhGetFormattedCounterValue.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(PDH_FMT_COUNTERVALUE_DOUBLE),
    ]
    PdhGetFormattedCounterValue.restype = wintypes.DWORD

    PdhGetFormattedCounterArray = pdh.PdhGetFormattedCounterArrayW
    PdhGetFormattedCounterArray.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    PdhGetFormattedCounterArray.restype = wintypes.DWORD

    return {
        "PdhOpenQuery": PdhOpenQuery,
        "PdhAddEnglishCounter": PdhAddEnglishCounter,
        "PdhCollectQueryData": PdhCollectQueryData,
        "PdhGetFormattedCounterValue": PdhGetFormattedCounterValue,
        "PdhGetFormattedCounterArray": PdhGetFormattedCounterArray,
    }


PDH = _init_pdh_functions()


class PDHQuery:
    """Wrapper for a PDH query supporting wildcard counters."""

    def __init__(self) -> None:
        self._query = wintypes.HANDLE()
        self._counters: dict[str, wintypes.HANDLE] = {}
        status = PDH["PdhOpenQuery"](None, None, ctypes.byref(self._query))
        if status != ERROR_SUCCESS:
            raise PDHError(f"PdhOpenQuery failed: {fmt_error(status)}")

    def add_counter(self, key: str, path: str) -> wintypes.HANDLE | None:
        counter = wintypes.HANDLE()
        status = PDH["PdhAddEnglishCounter"](self._query, path, 0, ctypes.byref(counter))
        if status != ERROR_SUCCESS:
            return None
        self._counters[key] = counter
        return counter

    def collect(self) -> bool:
        status = PDH["PdhCollectQueryData"](self._query)
        return status == ERROR_SUCCESS

    def get_value(self, key: str) -> float | None:
        counter = self._counters.get(key)
        if not counter:
            return None
        fmt = PDH_FMT_COUNTERVALUE_DOUBLE()
        status = PDH["PdhGetFormattedCounterValue"](counter, PDH_FMT_DOUBLE, None, ctypes.byref(fmt))
        if status != ERROR_SUCCESS or fmt.CStatus != ERROR_SUCCESS:
            return None
        return fmt.doubleValue

    def _get_base_array(self, key: str) -> tuple[int, _Pointer[PDH_FMT_COUNTERVALUE_ITEM_DOUBLE] | None]:
        counter = self._counters.get(key)
        if not counter:
            return 0, None

        buf_size = wintypes.DWORD(0)
        item_count = wintypes.DWORD(0)
        status = PDH["PdhGetFormattedCounterArray"](counter, PDH_FMT_DOUBLE, ctypes.byref(buf_size), ctypes.byref(item_count), None)

        if status != PDH_MORE_DATA:
            return 0, None

        buffer = (ctypes.c_byte * buf_size.value)()
        status = PDH["PdhGetFormattedCounterArray"](
            counter,
            PDH_FMT_DOUBLE,
            ctypes.byref(buf_size),
            ctypes.byref(item_count),
            ctypes.cast(buffer, ctypes.c_void_p),
        )
        if status != ERROR_SUCCESS:
            return 0, None

        array_ptr = ctypes.cast(buffer, ctypes.POINTER(PDH_FMT_COUNTERVALUE_ITEM_DOUBLE))
        return item_count.value, array_ptr

    def get_array(self, key: str) -> list[float | None]:
        item_count, array_ptr = self._get_base_array(key)
        if item_count == 0:
            return []

        readings: list[float | None] = []
        for idx in range(item_count):
            item = array_ptr[idx]
            if item.FmtValue.CStatus == ERROR_SUCCESS:
                readings.append(item.FmtValue.doubleValue)
            else:
                readings.append(None)
        return readings

    def get_dict(self, key: str) -> dict[str, float | None]:
        item_count, array_ptr = self._get_base_array(key)
        if item_count == 0:
            return {}

        readings: dict[str, float | None] = {}
        for idx in range(item_count):
            item = array_ptr[idx]
            readings[item.szName.lower()] = (
                item.FmtValue.doubleValue if item.FmtValue.CStatus == ERROR_SUCCESS else None
            )

        return readings