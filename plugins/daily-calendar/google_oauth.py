"""Google Calendar OAuth 2.0 PKCE primitives.

No web routes or credentials are exposed here. A future authenticated ULS
dashboard integration owns the callback and stores tokens privately.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from urllib.parse import urlencode, urlsplit

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
STATE_LIFETIME_SECONDS = 600


def _b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def new_request(client_id, redirect_uri, now=None):
    """Create a PKCE authorization request and short-lived pending state.

    The caller must store the returned pending dictionary server-side, never
    in a browser URL or portable backup. The verifier is not a client secret.
    """
    if not client_id or not isinstance(client_id, str):
        raise ValueError("OAuth client ID is required")
    parsed = urlsplit(redirect_uri)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("OAuth redirect URI must be HTTPS without credentials or fragment")
    verifier = _b64url(secrets.token_bytes(48))
    state = secrets.token_urlsafe(32)
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    pending = {"state": state, "verifier": verifier,
               "expires_at": (time.time() if now is None else now) + STATE_LIFETIME_SECONDS,
               "redirect_uri": redirect_uri}
    params = {"client_id": client_id, "redirect_uri": redirect_uri,
              "response_type": "code", "scope": SCOPE,
              "code_challenge": challenge, "code_challenge_method": "S256",
              "state": state, "access_type": "offline",
              "prompt": "consent"}
    return AUTH_ENDPOINT + "?" + urlencode(params), pending


def validate_callback(pending, state, code, redirect_uri, now=None):
    """Validate callback parameters before exchanging an authorization code.

    Caller must consume pending state exactly once, even if validation fails.
    """
    if not isinstance(pending, dict) or not isinstance(state, str) or not isinstance(code, str):
        raise ValueError("Invalid OAuth callback")
    if not state or not hmac.compare_digest(str(pending.get("state", "")), state):
        raise ValueError("OAuth state mismatch")
    if (time.time() if now is None else now) >= pending.get("expires_at", 0):
        raise ValueError("OAuth request expired")
    if redirect_uri != pending.get("redirect_uri") or not code.strip():
        raise ValueError("Invalid OAuth callback")
    verifier = pending.get("verifier")
    if not isinstance(verifier, str) or not 43 <= len(verifier) <= 128:
        raise ValueError("Invalid OAuth verifier")
    return {"code": code, "code_verifier": verifier, "redirect_uri": redirect_uri}


def token_exchange_fields(client_id, callback):
    """Build token request body; transport is intentionally not implemented."""
    return {"client_id": client_id, "code": callback["code"],
            "code_verifier": callback["code_verifier"],
            "redirect_uri": callback["redirect_uri"],
            "grant_type": "authorization_code"}
