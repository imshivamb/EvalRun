"""Unit tests for system doctor diagnostics (cli/doctor.py)."""

import unittest

from cli.doctor import run_doctor_checks
from cli.main import create_parser, doctor_command


class TestSystemDoctor(unittest.TestCase):

    def test_run_doctor_checks(self):
        all_ok, lines = run_doctor_checks()
        output = "\n".join(lines)

        self.assertIn("EVALRUN SYSTEM DOCTOR", output)
        self.assertIn("Python Version:", output)
        self.assertIn("EvalRun Version:", output)
        self.assertIn("Model API Keys Configured:", output)
        self.assertIn("Built-in Agent Import:", output)
        self.assertIn("Hosted Endpoint Reachability:", output)
        self.assertIn("Local Model Server:", output)
        self.assertIn("Output Directory Write Access:", output)
        self.assertIn("Doctor Verdict:", output)

    def test_doctor_command_cli_execution(self):
        parser = create_parser()
        args = parser.parse_args(["doctor"])
        exit_code = doctor_command(args)

        # In standard workspace setup with Python >= 3.9 and writable dir, doctor returns 0
        self.assertIn(exit_code, (0, 2))


if __name__ == "__main__":
    unittest.main()
