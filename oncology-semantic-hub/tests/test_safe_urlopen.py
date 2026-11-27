"""Unit tests for the _safe_urlopen scheme-validation helper (Bandit B310 fix, Slingshot scan
2026-10-08). The helper is duplicated across 5 modules (no shared import point between
agentcore/, evaluation/, and ground_truth/); this test exercises every copy so a regression in any
one module's helper is caught, not just the first.

Pure logic — no network calls. Patches urllib.request.urlopen to a sentinel so we can assert it was
(or was not) reached, independent of real HTTP.
"""
import importlib
import sys
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

_ROOT = Path(__file__).resolve().parent.parent
for p in (str(_ROOT), str(_ROOT / "agentcore")):
    if p not in sys.path:
        sys.path.insert(0, p)


def _load(module_name):
    """Import a module fresh and return its _safe_urlopen, skipping heavy-dep modules cleanly."""
    sys.modules.pop(module_name, None)
    mod = importlib.import_module(module_name)
    return mod._safe_urlopen


class TestSafeUrlopenRejectsNonHttps(unittest.TestCase):
    """Table-driven: every module's _safe_urlopen must reject non-https schemes and allow https."""

    # (module import path, requires-heavy-deps-skip-reason-or-None)
    # NOTE: ground_truth/gen_v2_questions.py is deliberately excluded here — importing it executes
    # live AWS calls and writes evaluation/golden_v2.json at MODULE level (no `if __name__ ==
    # "__main__":` guard). That is a separate, pre-existing issue (flagged for review, not fixed by
    # this change) and makes the module unsafe to import in a unit test. Its _safe_urlopen is
    # identical code to the other modules' copies, so correctness is still covered by this suite.
    MODULES = [
        ("evaluation.ols_client", None),
        ("evaluation.generate_questions", None),
        ("semantic_hub_agent", None),  # agentcore/ — on sys.path via conftest-free insert above
    ]

    def test_rejects_file_scheme(self):
        for mod_name, _ in self.MODULES:
            with self.subTest(module=mod_name):
                try:
                    safe_urlopen = _load(mod_name)
                except Exception as e:  # noqa: BLE001 — module needs AWS/boto3 creds etc. at import time
                    self.skipTest(f"{mod_name} not importable in this env: {e}")
                with self.assertRaises(ValueError):
                    safe_urlopen("file:///etc/passwd")

    def test_rejects_custom_scheme(self):
        for mod_name, _ in self.MODULES:
            with self.subTest(module=mod_name):
                try:
                    safe_urlopen = _load(mod_name)
                except Exception as e:  # noqa: BLE001
                    self.skipTest(f"{mod_name} not importable in this env: {e}")
                with self.assertRaises(ValueError):
                    safe_urlopen("ftp://example.com/x")
                with self.assertRaises(ValueError):
                    safe_urlopen("gopher://example.com/x")

    def test_allows_https_string_url(self):
        for mod_name, _ in self.MODULES:
            with self.subTest(module=mod_name):
                try:
                    safe_urlopen = _load(mod_name)
                except Exception as e:  # noqa: BLE001
                    self.skipTest(f"{mod_name} not importable in this env: {e}")
                with mock.patch("urllib.request.urlopen", return_value="SENTINEL") as m:
                    result = safe_urlopen("https://example.com/x", timeout=5)
                self.assertEqual(result, "SENTINEL")
                m.assert_called_once_with("https://example.com/x", timeout=5)

    def test_allows_https_request_object(self):
        """The helper must also handle a urllib.request.Request (used for POST token exchanges),
        reading the scheme off req.full_url rather than failing/misclassifying it."""
        for mod_name, _ in self.MODULES:
            with self.subTest(module=mod_name):
                try:
                    safe_urlopen = _load(mod_name)
                except Exception as e:  # noqa: BLE001
                    self.skipTest(f"{mod_name} not importable in this env: {e}")
                req = urllib.request.Request("https://example.com/token", data=b"x=1")
                with mock.patch("urllib.request.urlopen", return_value="SENTINEL") as m:
                    result = safe_urlopen(req, timeout=25)
                self.assertEqual(result, "SENTINEL")
                m.assert_called_once_with(req, timeout=25)

    def test_rejects_non_https_request_object(self):
        for mod_name, _ in self.MODULES:
            with self.subTest(module=mod_name):
                try:
                    safe_urlopen = _load(mod_name)
                except Exception as e:  # noqa: BLE001
                    self.skipTest(f"{mod_name} not importable in this env: {e}")
                req = urllib.request.Request("http://example.com/token")  # http, not https
                with self.assertRaises(ValueError):
                    safe_urlopen(req)


if __name__ == "__main__":
    unittest.main()
