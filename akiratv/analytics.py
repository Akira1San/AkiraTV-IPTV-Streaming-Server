# akiratv/analytics.py
import time
from collections import defaultdict, deque
from threading import Lock
from .stats import get_active_viewers

#import psutil

# try:
#     pynvml.nvmlInit()
#     NVML_AVAILABLE = True
# except Exception:
#     NVML_AVAILABLE = False


VIEWER_TIMEOUT = 30  # seconds
HISTORY_SECONDS = 3600  # 1 hour
SAMPLE_INTERVAL = 5     # seconds

_lock = Lock()

# channel -> ip -> last_seen
_active_viewers = defaultdict(dict)

# channel -> deque[(timestamp, count)]
_history = defaultdict(lambda: deque(maxlen=HISTORY_SECONDS // SAMPLE_INTERVAL))

SYSTEM_HISTORY = deque(maxlen=720)

def record_system_stats():
    print("📊 System stats sampled")
    """Record CPU/GPU/RAM + total viewers over time."""
    while True:
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent

        gpu = 0
        if NVML_AVAILABLE:
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                gpu = util.gpu
            except Exception:
                gpu = 0

        viewers = sum(get_current_viewers().values())

        with _lock:
            SYSTEM_HISTORY.append({
                "time": int(time.time()),
                "cpu": cpu,
                "gpu": gpu,
                "ram_percent": mem,
                "viewers": viewers
            })

        #time.sleep(SAMPLE_INTERVAL)
        time.sleep(5)


def record_view(channel: str, ip: str):
    now = time.time()
    with _lock:
        _active_viewers[channel][ip] = now


def cleanup_and_sample():
    """Remove stale viewers and store time-series data"""
    now = time.time()

    with _lock:
        for channel, viewers in _active_viewers.items():
            stale = [
                ip for ip, last in viewers.items()
                if now - last > VIEWER_TIMEOUT
            ]
            for ip in stale:
                del viewers[ip]

            # Record sample
            _history[channel].append((now, len(viewers)))


def get_current_viewers():
    with _lock:
        return {ch: len(v) for ch, v in _active_viewers.items()}


def get_history(channel: str):
    with _lock:
        return list(_history[channel])

def get_system_history():
    with _lock:
        return list(SYSTEM_HISTORY)

