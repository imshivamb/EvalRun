"""Unit tests for system doctor diagnostics (cli/doctor.py)."""

import os
import unittest

import pytest

from cli.doctor import run_doctor_checks
from cli.main import create_parser, doctor_command


class TestSystemDoctor(unittest.TestCase):
    """Offline doctor checks used in CI."""

    def setUp(self):
        self._previous_skip_network = os.environ.get("EVALRUN_SKIP_NETWORK_CHECKS")
        os.environ["EVALRUN_SKIP_NETWORK_CHECKS"] = "1"

    def tearDown(self):
        if self._previous_skip_network is None:
            os.environ.pop("EVALRUN_SKIP_NETWORK_CHECKS", None)
        else:
            os.environ["EVALRUN_SKIP_NETWORK_CHECKS"] = self._previous_skip_network

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
        self.assertIn("EVALRUN_SKIP_NETWORK_CHECKS=1", output)

    def test_doctor_command_cli_execution(self):
        parser = create_parser()
        args = parser.parse_args(["doctor"])
        exit_code = doctor_command(args)

        # In standard workspace setup with Python >= 3.9 and writable dir, doctor returns 0
        self.assertIn(exit_code, (0, 2))


@pytest.mark.network
class TestSystemDoctorNetwork(unittest.TestCase):
    """Optional live probes; skipped in CI with pytest -m 'not network'."""

    def test_reachability_lines_exist_without_skip_flag(self):
        previous = os.environ.pop("EVALRUN_SKIP_NETWORK_CHECKS", None)
        try:
            _, lines = run_doctor_checks()
            output = "\n".join(lines)
            self.assertIn("Hosted Endpoint Reachability:", output)
            self.assertIn("Local Model Server:", output)
            self.assertNotIn("EVALRUN_SKIP_NETWORK_CHECKS=1", output)
        finally:
            if previous is not None:
                os.environ["EVALRUN_SKIP_NETWORK_CHECKS"] = previous


if __name__ == "__main__":
    unittest.main()
