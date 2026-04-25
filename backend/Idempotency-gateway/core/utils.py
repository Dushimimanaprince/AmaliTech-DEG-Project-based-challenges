import threading

_locks = {}
_locks_lock = threading.Lock()

def get_lock_for_key(key: str) -> threading.Lock:
    with _locks_lock:
        if key not in _locks:
            _locks[key] = threading.Lock()
        return _locks[key]