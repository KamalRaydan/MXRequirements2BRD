"""Keystore caches reads so macOS only prompts for Keychain access once per run."""
import pytest

import keyring

from services import keystore


@pytest.fixture(autouse=True)
def fresh_cache():
    # Each test starts with an empty cache so reads are deterministic
    keystore._cache.clear()
    yield
    keystore._cache.clear()


@pytest.fixture
def counting_keyring(monkeypatch):
    """Stand-in Keychain that counts how many times it is actually read."""
    store: dict[tuple[str, str], str] = {}
    reads = {"count": 0}

    def get(service, account):
        reads["count"] += 1
        return store.get((service, account))

    monkeypatch.setattr(keyring, "get_password",
                        lambda s, a: get(s, a))
    monkeypatch.setattr(keyring, "set_password",
                        lambda s, a, v: store.__setitem__((s, a), v))
    monkeypatch.setattr(keyring, "delete_password",
                        lambda s, a: store.pop((s, a), None))
    return store, reads


def test_repeated_reads_hit_keychain_once(counting_keyring):
    store, reads = counting_keyring
    # Seed the Keychain as if a key was saved in a previous session
    store[(keystore.config.KEYRING_SERVICE, "api_key_openai")] = "sk-test"

    # Five reads (what a Settings page load roughly triggers) -> one Keychain hit
    for _ in range(5):
        assert keystore.get_api_key("openai") == "sk-test"
    assert reads["count"] == 1


def test_set_then_delete_updates_cache(counting_keyring):
    store, reads = counting_keyring
    keystore.set_api_key("openai", "sk-test")
    assert keystore.is_configured("openai") is True

    keystore.delete_api_key("openai")
    # delete must clear the cached value, not keep serving the old key
    assert keystore.get_api_key("openai") is None
