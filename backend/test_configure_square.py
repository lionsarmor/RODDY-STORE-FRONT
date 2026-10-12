"""Failed credential checks must explain recovery without leaking secrets or saving."""
import contextlib
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError


spec = importlib.util.spec_from_file_location(
    "configure_square", Path(__file__).parent / "deploy" / "configure-square.py"
)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class ConfigureSquareTests(unittest.TestCase):
    def test_failures_are_safe_and_actionable(self):
        secret = "private-test-token-never-display"
        cases = [
            (HTTPError("https://example.invalid", 401, secret, {}, io.BytesIO(secret.encode())), "Production"),
            (HTTPError("https://example.invalid", 403, secret, {}, None), "permissions"),
            (HTTPError("https://example.invalid", 429, secret, {}, None), "rate limit"),
            (HTTPError("https://example.invalid", 503, secret, {}, None), "temporarily unavailable"),
            (HTTPError("https://example.invalid", 400, secret, {}, None), "HTTP 400"),
            (URLError(secret), "network/DNS"),
            (TimeoutError(secret), "network/DNS"),
            (ValueError(secret), "unreadable response"),
        ]
        for error, expected in cases:
            with self.subTest(expected=expected):
                output = io.StringIO()
                with patch("sys.argv", ["configure-square.py", "--mode", "live"]), \
                     patch.object(setup.os, "geteuid", return_value=0), \
                     patch.object(setup.getpass, "getpass", return_value=secret), \
                     patch.object(setup, "urlopen", side_effect=error), \
                     patch.object(setup.Path, "write_text") as write, \
                     patch.object(setup.subprocess, "run") as restart, \
                     contextlib.redirect_stderr(output), \
                     self.assertRaises(SystemExit) as raised:
                    setup.main()
                self.assertEqual(raised.exception.code, 2)
                self.assertIn(expected, output.getvalue())
                self.assertIn("Nothing saved", output.getvalue())
                self.assertNotIn(secret, output.getvalue())
                write.assert_not_called()
                restart.assert_not_called()


if __name__ == "__main__":
    unittest.main()
