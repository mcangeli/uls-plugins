"""Offline tests for PKCE and callback validation."""
import importlib.util
from pathlib import Path
import unittest
from urllib.parse import parse_qs, urlsplit

spec = importlib.util.spec_from_file_location("google_oauth", Path(__file__).with_name("google_oauth.py"))
oauth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oauth)


class OAuthTests(unittest.TestCase):
    def setUp(self):
        self.redirect = "https://scoreboard.example/authorized/google/callback"
        self.url, self.pending = oauth.new_request("client-id", self.redirect, now=100)

    def test_pkce_and_minimum_scope(self):
        q = parse_qs(urlsplit(self.url).query)
        self.assertEqual(q["scope"], [oauth.SCOPE])
        self.assertEqual(q["code_challenge_method"], ["S256"])
        self.assertNotIn(self.pending["verifier"], self.url)
        self.assertEqual(q["state"], [self.pending["state"]])
        self.assertEqual(q["access_type"], ["offline"])

    def test_callback_and_token_fields(self):
        callback = oauth.validate_callback(self.pending, self.pending["state"], "auth-code", self.redirect, now=101)
        self.assertEqual(oauth.token_exchange_fields("client-id", callback)["grant_type"], "authorization_code")

    def test_reject_mismatched_expired_and_empty_callbacks(self):
        with self.assertRaises(ValueError):
            oauth.validate_callback(self.pending, "wrong", "code", self.redirect, now=101)
        with self.assertRaises(ValueError):
            oauth.validate_callback(self.pending, self.pending["state"], "code", self.redirect, now=700)
        with self.assertRaises(ValueError):
            oauth.validate_callback(self.pending, self.pending["state"], "", self.redirect, now=101)
        with self.assertRaises(ValueError):
            oauth.validate_callback(self.pending, self.pending["state"], "code", "https://other.example/callback", now=101)

    def test_reject_insecure_redirect(self):
        for uri in ("http://example.com/cb", "https://user:pass@example.com/cb", "https://example.com/cb#fragment"):
            with self.assertRaises(ValueError):
                oauth.new_request("client-id", uri)


if __name__ == "__main__":
    unittest.main()
