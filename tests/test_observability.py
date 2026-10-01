"""Langfuse tracing stays off unless the package is installed and keys are configured."""

import os
import unittest
from unittest.mock import MagicMock, patch

import framework.observability as observability


def sample(value):
    return value * 2


class TestObservability(unittest.TestCase):
    def test_no_keys_means_plain_decorator(self):
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(observability, "_langfuse_observe", MagicMock()) as langfuse:
            self.assertFalse(observability.langfuse_enabled())
            wrapped = observability.observe()(sample)
            self.assertEqual(wrapped(3), 6)
            langfuse.assert_not_called()

    def test_package_and_keys_enable_langfuse(self):
        keys = {"LANGFUSE_PUBLIC_KEY": "pk", "LANGFUSE_SECRET_KEY": "sk"}
        with patch.dict(os.environ, keys, clear=True), \
                patch.object(observability, "_langfuse_observe", MagicMock()) as langfuse:
            self.assertTrue(observability.langfuse_enabled())
            observability.observe(name="x")
            langfuse.assert_called_once_with(name="x")

    def test_missing_package_means_plain_decorator(self):
        keys = {"LANGFUSE_PUBLIC_KEY": "pk", "LANGFUSE_SECRET_KEY": "sk"}
        with patch.dict(os.environ, keys, clear=True), \
                patch.object(observability, "_langfuse_observe", None):
            self.assertFalse(observability.langfuse_enabled())
            self.assertEqual(observability.observe()(sample)(4), 8)


if __name__ == "__main__":
    unittest.main()
