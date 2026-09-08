from __future__ import annotations

import os
import threading
import time


_last_renewal = time.monotonic()
_lock = threading.Lock()


def renew() -> float:
    global _last_renewal
    with _lock:
        _last_renewal = time.monotonic()
        return _last_renewal


def start_monitor(on_expired, timeout_s: float = 15.0) -> None:
    if os.environ.get("ACE_LEASE_REQUIRED") != "1": return
    def monitor() -> None:
        while True:
            time.sleep(1)
            with _lock: elapsed = time.monotonic() - _last_renewal
            if elapsed >= timeout_s:
                on_expired(); return
    threading.Thread(target=monitor, daemon=True, name="ace-runtime-lease").start()
