from cakrawala.web.cache import TTLCache


def test_cache_reuses_value_before_expiry() -> None:
    cache = TTLCache(max_entries=2)
    calls = 0

    def loader() -> str:
        nonlocal calls
        calls += 1
        return "evidence"

    assert cache.get("key", 60, loader) == "evidence"
    assert cache.get("key", 60, loader) == "evidence"
    assert calls == 1


def test_clear_forces_next_load() -> None:
    cache = TTLCache(max_entries=2)
    values = iter(["first", "second"])

    assert cache.get("key", 60, lambda: next(values)) == "first"
    cache.clear()
    assert cache.get("key", 60, lambda: next(values)) == "second"


def test_invalid_cache_configuration_fails_closed() -> None:
    try:
        TTLCache(max_entries=0)
    except ValueError as exc:
        assert "positive" in str(exc)
    else:
        raise AssertionError("invalid cache size should fail")
