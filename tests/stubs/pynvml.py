import os
from types import SimpleNamespace as NS
NVML_TEMPERATURE_GPU = 0; NVML_CLOCK_GRAPHICS = 0
def nvmlInit():
    if os.environ.get("NVFAIL"): raise RuntimeError("no nvidia")
def nvmlShutdown(): pass
def nvmlDeviceGetHandleByIndex(i): return 1
def nvmlDeviceGetName(h): return b"NVIDIA GeForce RTX 3060 Laptop GPU"
def nvmlDeviceGetUtilizationRates(h): return NS(gpu=57)
def nvmlDeviceGetTemperature(h, k): return 68
def nvmlDeviceGetPowerUsage(h): return 92000
def nvmlDeviceGetClockInfo(h, k): return 1830
def nvmlDeviceGetMemoryInfo(h): return NS(used=3.2*1024**3, total=6*1024**3)
def nvmlDeviceGetFanSpeed(h): return 41
def nvmlSystemGetDriverVersion(): return b'536.23'
