import pytest

from app.config import Settings
from app.llm import cache, provider

SCHEMA = {"type": "object"}


def settings(llm_provider="gemini", key="k", model="gemini-test", demo=False):
    return Settings(
        llm_provider=llm_provider, gemini_api_key=key, gemini_model=model,
        ollama_model="ollama-test", demo_mode=demo, show_unverified=False,
    )


class Fake:
    def __init__(self, *results):
        self.results = list(results)
        self.calls = 0

    def __call__(self, *args):
        self.calls += 1
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)


def use(monkeypatch, config, gemini=None, ollama=None):
    gemini = gemini or Fake()
    ollama = ollama or Fake()
    monkeypatch.setattr(provider, "get_settings", lambda: config)
    monkeypatch.setattr(provider, "_call_gemini", gemini)
    monkeypatch.setattr(provider, "_call_ollama", ollama)
    return gemini, ollama


def ask():
    return provider.complete_json("sys", "user", SCHEMA)


def test_gemini_answers_first(monkeypatch):
    _, ollama = use(monkeypatch, settings(), Fake('{"a": 1}'))

    assert ask() == {"a": 1}
    assert ollama.calls == 0


def test_falls_back_to_ollama_on_gemini_error(monkeypatch):
    use(monkeypatch, settings(), Fake(TimeoutError()), Fake('{"a": 2}'))

    assert ask() == {"a": 2}


def test_falls_back_on_invalid_json(monkeypatch):
    use(monkeypatch, settings(), Fake("not json"), Fake('{"a": 3}'))

    assert ask() == {"a": 3}


def test_non_object_json_is_rejected(monkeypatch):
    use(monkeypatch, settings(), Fake("[1, 2]"), Fake("7"))

    assert ask() is None


def test_returns_none_when_every_provider_fails(monkeypatch):
    use(monkeypatch, settings(), Fake(TimeoutError()), Fake(OSError()))

    assert ask() is None


def test_provider_none_makes_no_calls(monkeypatch):
    gemini, ollama = use(monkeypatch, settings("none"))

    assert ask() is None
    assert gemini.calls == ollama.calls == 0


def test_missing_gemini_key_goes_straight_to_ollama(monkeypatch):
    gemini, _ = use(monkeypatch, settings(key=""), ollama=Fake('{"a": 4}'))

    assert ask() == {"a": 4}
    assert gemini.calls == 0


def test_ollama_provider_never_calls_gemini(monkeypatch):
    gemini, _ = use(monkeypatch, settings("ollama"), ollama=Fake('{"a": 5}'))

    assert ask() == {"a": 5}
    assert gemini.calls == 0


def test_second_call_comes_from_the_cache(monkeypatch):
    gemini, _ = use(monkeypatch, settings(), Fake('{"a": 6}'))

    assert ask() == ask() == {"a": 6}
    assert gemini.calls == 1


def test_failures_are_not_cached(monkeypatch):
    gemini, ollama = use(monkeypatch, settings(), Fake(TimeoutError(), '{"a": 7}'), Fake(OSError()))

    assert ask() is None
    assert ask() == {"a": 7}
    assert (gemini.calls, ollama.calls) == (2, 1)


def test_cache_separates_providers_and_prompts(monkeypatch):
    cache.put("p1", "x", {"v": 1})
    cache.put("p2", "x", {"v": 2})
    cache.put("p1", "y", {"v": 3})

    assert [cache.get("p1", "x"), cache.get("p2", "x"), cache.get("p1", "y")] == [{"v": 1}, {"v": 2}, {"v": 3}]
    assert cache.get("p2", "y") is None


def test_demo_mode_replays_the_cache_without_calls(monkeypatch):
    use(monkeypatch, settings(), Fake('{"a": 8}'))
    ask()

    gemini, ollama = use(monkeypatch, settings(demo=True))

    assert ask() == {"a": 8}
    assert gemini.calls == ollama.calls == 0


def test_demo_mode_miss_returns_none_without_calls(monkeypatch):
    gemini, ollama = use(monkeypatch, settings(demo=True))

    assert ask() is None
    assert gemini.calls == ollama.calls == 0


def test_availability(monkeypatch):
    use(monkeypatch, settings("none"))
    assert provider.is_available() is False

    use(monkeypatch, settings())
    assert provider.is_available() is True

    use(monkeypatch, settings("ollama"))
    monkeypatch.setattr(provider, "_ollama_reachable", lambda: False)
    assert provider.is_available() is False
