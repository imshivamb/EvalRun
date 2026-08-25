"""Unit tests for scenario validation module (cli/validator.py)."""

import os
import shutil
import tempfile
import unittest

from cli.validator import validate_scenario
from cli.main import create_parser, validate_command


class TestScenarioValidator(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_validate_valid_scenario(self):
        scenario_path = os.path.join(self.temp_dir, "valid_scenario.md")
        content = """---
benchmark_id: test-valid-001
name: Valid Test Scenario
profile: travel-agent
---

# Description
Valid description.

# User Prompt
Valid prompt.

# Extracted Constraints
- Constraint 1

# Expected Behaviour
Expected behavior description.

# Evaluation Criteria
### Constraint Satisfaction
Rubric for constraint satisfaction.

### Planning Quality
Rubric for planning quality.

## Information Accuracy
Rubric for information accuracy.

## Personalization
Rubric for personalization.

## Adaptability
Rubric for adaptability.

# Pass Criteria
Score >= 75.0

# Failure Conditions
Over budget.
"""
        with open(scenario_path, "w", encoding="utf-8") as f:
            f.write(content)

        is_valid, errors, details = validate_scenario(scenario_path)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        self.assertEqual(details["benchmark_id"], "test-valid-001")
        self.assertEqual(details["name"], "Valid Test Scenario")
        self.assertIn("Constraint Satisfaction", details["dimensions"])
        self.assertIn("Information Accuracy", details["dimensions"])

        parser = create_parser()
        args = parser.parse_args(["validate", scenario_path])
        exit_code = validate_command(args)
        self.assertEqual(exit_code, 0)

    def test_validate_missing_file(self):
        missing_path = os.path.join(self.temp_dir, "non_existent.md")
        is_valid, errors, details = validate_scenario(missing_path)

        self.assertFalse(is_valid)
        self.assertTrue(any("not found" in e for e in errors))
        self.assertTrue(any("How to fix" in e for e in errors))

    def test_validate_malformed_frontmatter(self):
        broken_yaml_path = os.path.join(self.temp_dir, "broken_yaml.md")
        content = """---
benchmark_id: test-001
name: Broken YAML
profile: [invalid yaml syntax {{
---

# Description
Test.
"""
        with open(broken_yaml_path, "w", encoding="utf-8") as f:
            f.write(content)

        is_valid, errors, details = validate_scenario(broken_yaml_path)
        self.assertFalse(is_valid)
        self.assertTrue(any("Malformed YAML frontmatter" in e for e in errors))
        self.assertTrue(any("How to fix" in e for e in errors))

    def test_validate_unsupported_profile(self):
        bad_profile_path = os.path.join(self.temp_dir, "bad_profile.md")
        content = """---
benchmark_id: test-bad-prof
name: Bad Profile Scenario
profile: non-existent-profile-xyz
---

# Description
Desc.

# User Prompt
Prompt.

# Extracted Constraints
- C1

# Expected Behaviour
Behavior.

# Evaluation Criteria
### Constraint Satisfaction
Criteria.

# Pass Criteria
Pass.

# Failure Conditions
Fail.
"""
        with open(bad_profile_path, "w", encoding="utf-8") as f:
            f.write(content)

        is_valid, errors, details = validate_scenario(bad_profile_path)
        self.assertFalse(is_valid)
        self.assertTrue(any("Unsupported profile" in e for e in errors))
        self.assertTrue(any("travel-agent" in e for e in errors))
        self.assertTrue(any("How to fix" in e for e in errors))

    def test_validate_missing_sections(self):
        missing_sec_path = os.path.join(self.temp_dir, "missing_sec.md")
        content = """---
benchmark_id: test-missing-sec
name: Missing Sections
profile: travel-agent
---

# Description
Desc.

# User Prompt
Prompt.
"""
        with open(missing_sec_path, "w", encoding="utf-8") as f:
            f.write(content)

        is_valid, errors, details = validate_scenario(missing_sec_path)
        self.assertFalse(is_valid)
        self.assertTrue(any("Missing required section" in e for e in errors))

    def test_validate_unsupported_dimension(self):
        bad_dim_path = os.path.join(self.temp_dir, "bad_dim.md")
        content = """---
benchmark_id: test-bad-dim
name: Bad Dimension
profile: travel-agent
---

# Description
Desc.

# User Prompt
Prompt.

# Extracted Constraints
- C1

# Expected Behaviour
Behavior.

# Evaluation Criteria
### NonExistentDimensionName
Rubric.

# Pass Criteria
Pass.

# Failure Conditions
Fail.
"""
        with open(bad_dim_path, "w", encoding="utf-8") as f:
            f.write(content)

        is_valid, errors, details = validate_scenario(bad_dim_path)
        self.assertFalse(is_valid)
        self.assertTrue(any("is not supported by profile" in e for e in errors))
        self.assertTrue(any("How to fix" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
