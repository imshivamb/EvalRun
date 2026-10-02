"""Argument errors must never echo an API key value."""

import unittest
from contextlib import redirect_stderr
from io import StringIO

from cli.main import create_parser

SECRET = "AQ.not-a-real-key-0123456789"


class TestArgumentErrorRedaction(unittest.TestCase):
    def _error_output(self, argv):
        stderr = StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as exit_info:
            create_parser().parse_args(argv)
        self.assertEqual(exit_info.exception.code, 2)
        return stderr.getvalue()

    def test_unsplit_option_string_is_redacted(self):
        # A shell that does not word-split a variable passes every option as
        # one unrecognized argument, which argparse echoes verbatim.
        output = self._error_output(["run", f"--model m --api-key {SECRET} --trials 3"])
        self.assertNotIn(SECRET, output)
        self.assertIn("--api-key [REDACTED]", output)

    def test_recognized_api_key_is_not_echoed(self):
        output = self._error_output(["run", "--api-key", SECRET, "--no-such-flag"])
        self.assertNotIn(SECRET, output)

    def test_equals_form_and_judge_key(self):
        output = self._error_output(
            ["run", f"--judge-api-key={SECRET}", f"--auditor-api-key={SECRET}", "--bogus"]
        )
        self.assertNotIn(SECRET, output)

    def test_subcommand_errors_are_redacted_too(self):
        output = self._error_output(["run", "--api-key", SECRET, "--trials", "many"])
        self.assertNotIn(SECRET, output)


if __name__ == "__main__":
    unittest.main()
