"""API key storage in the macOS Keychain via `keyring` (spec §3.1).

One Keychain entry per provider (account "api_key_anthropic", "api_key_openai")
so switching providers never discards the other key. Keys never touch the
database, logs, or any file. Milestone 3 swaps this module for Electron
safeStorage + header injection.
"""
import keyring

import config


def _account(provider: str) -> str:
    return f"api_key_{provider}"


def set_api_key(provider: str, value: str) -> None:
    keyring.set_password(config.KEYRING_SERVICE, _account(provider), value)


def get_api_key(provider: str) -> str | None:
    value = keyring.get_password(config.KEYRING_SERVICE, _account(provider))
    if not value and provider == "anthropic":
        # Fallback: key saved before multi-provider support existed
        value = keyring.get_password(config.KEYRING_SERVICE, config.KEYRING_LEGACY_ACCOUNT)
    return value


def delete_api_key(provider: str) -> None:
    for account in ([_account(provider), config.KEYRING_LEGACY_ACCOUNT]
                    if provider == "anthropic" else [_account(provider)]):
        try:
            keyring.delete_password(config.KEYRING_SERVICE, account)
        except keyring.errors.PasswordDeleteError:
            pass  # nothing stored — fine


def is_configured(provider: str) -> bool:
    return bool(get_api_key(provider))
