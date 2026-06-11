"""API key storage in the macOS Keychain via `keyring` (spec §3.1).

The key never touches the database, logs, or any file. Milestone 3 swaps this
module for Electron safeStorage + header injection.
"""
import keyring

import config


def set_api_key(value: str) -> None:
    keyring.set_password(config.KEYRING_SERVICE, config.KEYRING_ACCOUNT, value)


def get_api_key() -> str | None:
    return keyring.get_password(config.KEYRING_SERVICE, config.KEYRING_ACCOUNT)


def delete_api_key() -> None:
    try:
        keyring.delete_password(config.KEYRING_SERVICE, config.KEYRING_ACCOUNT)
    except keyring.errors.PasswordDeleteError:
        pass  # nothing stored — fine


def is_configured() -> bool:
    return bool(get_api_key())
