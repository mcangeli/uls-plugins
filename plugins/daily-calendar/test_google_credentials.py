"""Offline credential lifecycle tests; never contact Google."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("google_credentials", Path(__file__).with_name("google_credentials.py"))
credentials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(credentials)


class Response:
    def __init__(self, value):
        self.value = json.dumps(value).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        return self.value[:size]


class CredentialTests(unittest.TestCase):
    def test_private_save_load_and_disconnect(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root) / "oauth"
            credentials.save_tokens(directory, {
                "refresh_token": "secret-refresh", "access_token": "short-lived",
                "expires_at": 100, "scope": "calendar.readonly"})
            self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
            self.assertEqual((directory / "google-tokens.json").stat().st_mode & 0o777, 0o600)
            self.assertEqual(credentials.load_tokens(directory)["refresh_token"], "secret-refresh")
            credentials.disconnect(directory, opener=lambda req, timeout: Response({}))
            self.assertFalse((directory / "google-tokens.json").exists())

    def test_refresh_keeps_existing_refresh_token(self):
        result = credentials.refresh_access_token(
            "client-id", {"refresh_token": "old-refresh", "access_token": "expired"},
            opener=lambda req, timeout: Response({"access_token": "fresh", "expires_in": 300}))
        self.assertEqual(result["refresh_token"], "old-refresh")
        self.assertEqual(result["access_token"], "fresh")

    def test_private_directory_required(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root) / "oauth"
            directory.mkdir(mode=0o755)
            with self.assertRaises(credentials.CredentialError):
                credentials.save_tokens(directory, {"refresh_token": "secret"})

    def test_missing_refresh_token_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(credentials.CredentialError):
                credentials.save_tokens(Path(root) / "oauth", {"access_token": "only"})


if __name__ == "__main__":
    unittest.main()
