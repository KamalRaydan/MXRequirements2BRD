"""API key storage in the macOS Keychain via `keyring` (spec §3.1).

One Keychain entry per provider (account "api_key_anthropic", "api_key_openai")
so switching providers never discards the other key. Keys never touch the
database, logs, or any file. Milestone 3 swaps this module for Electron
safeStorage + header injection.

Reads are cached in memory for the life of the backend process. macOS shows a
Keychain access prompt on *every* read when the interpreter is not signed with a
stable identity (Homebrew/PyInstaller binaries are ad-hoc signed), so without the
cache a single app session triggers 5-10 prompts. This process is the only writer
of these entries, so the cache can never go stale within a run.
"""
import keyring

import config

# provider -> resolved key (None means "looked up, not configured")
_cache: dict[str, str | None] = {}


def _account(provider: str) -> str:
    return f"api_key_{provider}"


def set_api_key(provider: str, value: str) -> None:
    keyring.set_password(config.KEYRING_SERVICE, _account(provider), value)
    _cache[provider] = value


def get_api_key(provider: str) -> str | None:
    if provider in _cache:
        return _cache[provider]
    value = keyring.get_password(config.KEYRING_SERVICE, _account(provider))
    if not value and provider == "anthropic":
        # Fallback: key saved before multi-provider support existed
        value = keyring.get_password(config.KEYRING_SERVICE, config.KEYRING_LEGACY_ACCOUNT)
    _cache[provider] = value
    return value


def delete_api_key(provider: str) -> None:
    for account in ([_account(provider), config.KEYRING_LEGACY_ACCOUNT]
                    if provider == "anthropic" else [_account(provider)]):
        try:
            keyring.delete_password(config.KEYRING_SERVICE, account)
        except keyring.errors.PasswordDeleteError:
            pass  # nothing stored — fine
    _cache[provider] = None


def is_configured(provider: str) -> bool:
    return bool(get_api_key(provider))
