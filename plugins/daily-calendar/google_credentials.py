"""Private Google OAuth credential storage and refresh-token lifecycle.

Only a trusted, authenticated host integration may call these helpers.
Never expose the credential file via plugin settings or portable backups.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"
MAX_RESPONSE = 65536


class CredentialError(Exception):
    pass


def _validate_directory(path):
    directory = Path(path)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink() or (directory.stat().st_mode & 0o077):
        raise CredentialError("Credential directory must be private")
    return directory


def save_tokens(directory, tokens):
    """Atomically replace service-owned 0600 credentials."""
    directory = _validate_directory(directory)
    if not isinstance(tokens, dict) or not tokens.get("refresh_token"):
        raise CredentialError("Refresh token required")
    destination = directory / "google-tokens.json"
    if destination.is_symlink():
        raise CredentialError("Credential path must not be a symlink")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory,
                                         prefix=".google-", delete=False) as stream:
            temp_path = Path(stream.name)
            os.fchmod(stream.fileno(), 0o600)
            json.dump({key: tokens[key] for key in ("access_token", "refresh_token",
                       "expires_at", "token_type", "scope") if key in tokens}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, destination)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def load_tokens(directory):
    directory = _validate_directory(directory)
    path = directory / "google-tokens.json"
    if path.is_symlink():
        raise CredentialError("Credential path must not be a symlink")
    try:
        with path.open("r", encoding="utf-8") as stream:
            if path.stat().st_mode & 0o077:
                raise CredentialError("Credential file must be private")
            result = json.load(stream)
    except (OSError, ValueError):
        raise CredentialError("Google Calendar not connected") from None
    if not isinstance(result, dict) or not result.get("refresh_token"):
        raise CredentialError("Invalid Google Calendar credentials")
    return result


def _post(endpoint, fields, opener=urlopen):
    request = Request(endpoint, data=urlencode(fields).encode("utf-8"),
                      headers={"Content-Type": "application/x-www-form-urlencoded"},
                      method="POST")
    try:
        with opener(request, timeout=8) as response:
            data = response.read(MAX_RESPONSE + 1)
    except (HTTPError, URLError, OSError, TimeoutError):
        raise CredentialError("Google OAuth request failed") from None
    if len(data) > MAX_RESPONSE:
        raise CredentialError("Google OAuth response too large")
    try:
        result = json.loads(data)
    except (ValueError, UnicodeError):
        raise CredentialError("Invalid Google OAuth response") from None
    if not isinstance(result, dict):
        raise CredentialError("Invalid Google OAuth response")
    return result


def exchange_code(client_id, callback, opener=urlopen):
    from google_oauth import token_exchange_fields
    result = _post(TOKEN_ENDPOINT, token_exchange_fields(client_id, callback), opener)
    if not result.get("refresh_token") or not result.get("access_token"):
        raise CredentialError("Google did not return offline credentials")
    result["expires_at"] = time.time() + max(0, int(result.get("expires_in", 3600)))
    return result


def refresh_access_token(client_id, credentials, opener=urlopen):
    result = _post(TOKEN_ENDPOINT, {
        "client_id": client_id, "refresh_token": credentials["refresh_token"],
        "grant_type": "refresh_token",
    }, opener)
    if not result.get("access_token"):
        raise CredentialError("Google did not return an access token")
    updated = dict(credentials)
    updated["access_token"] = result["access_token"]
    updated["expires_at"] = time.time() + max(0, int(result.get("expires_in", 3600)))
    return updated


def disconnect(directory, opener=urlopen):
    """Delete local credentials even if remote revocation is unavailable."""
    credentials = None
    try:
        credentials = load_tokens(directory)
    except CredentialError:
        pass
    path = _validate_directory(directory) / "google-tokens.json"
    if path.is_symlink():
        raise CredentialError("Credential path must not be a symlink")
    path.unlink(missing_ok=True)
    if credentials:
        token = credentials.get("refresh_token")
        if token:
            try:
                request = Request(REVOKE_ENDPOINT, data=urlencode({"token": token}).encode(),
                                  headers={"Content-Type": "application/x-www-form-urlencoded"},
                                  method="POST")
                with opener(request, timeout=8) as response:
                    response.read(1024)
            except (HTTPError, URLError, OSError, TimeoutError):
                pass
