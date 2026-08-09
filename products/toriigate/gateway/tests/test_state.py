import time

from toriigate.state import MemoryStore, store_from_env


def test_sliding_window_counts_within_window():
    s = MemoryStore(window_seconds=10)
    base = time.time()
    for i in range(5):
        n = s.hit("1.2.3.4", now=base + i * 0.1)
    assert n == 5
    # a request far in the future sees the old ones aged out
    assert s.hit("1.2.3.4", now=base + 100) == 1


def test_windows_are_per_key():
    s = MemoryStore(window_seconds=10)
    now = time.time()
    s.hit("a", now)
    s.hit("a", now)
    s.hit("b", now)
    assert s.count("a", now) == 2
    assert s.count("b", now) == 1


def test_offenders_increment_and_expire():
    s = MemoryStore(window_seconds=10, offender_ttl=0.05)
    assert s.incr_offender("9.9.9.9") == 1
    assert s.incr_offender("9.9.9.9") == 2
    assert s.get_offender("9.9.9.9") == 2
    time.sleep(0.06)
    assert s.get_offender("9.9.9.9") == 0


def test_store_from_env_defaults_to_memory(monkeypatch):
    monkeypatch.delenv("TORII_REDIS_URL", raising=False)
    assert isinstance(store_from_env(10), MemoryStore)
