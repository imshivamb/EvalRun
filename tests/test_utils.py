import unittest

from framework.utils import parse_json_markdown


class TestJsonMarkdownParsing(unittest.TestCase):
    def test_repairs_trailing_comma_from_llm_json(self):
        parsed = parse_json_markdown('{"score": 85, "reason": "Good plan",}')
        self.assertEqual(parsed["score"], 85)
        self.assertEqual(parsed["reason"], "Good plan")


if __name__ == "__main__":
    unittest.main()
