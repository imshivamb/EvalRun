"""Scenario validation module for evalrun validate command."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from framework.parsers.frontmatter import parse_frontmatter
from framework.parsers.markdown import parse_sections
from framework.profiles import PROFILE_REGISTRY
from framework.profiles.registry import get_custom_profile


REQUIRED_SECTIONS = [
    "description",
    "user prompt",
    "extracted constraints",
    "expected behaviour",
    "evaluation criteria",
    "pass criteria",
    "failure conditions",
]

# Section alias mapping
SECTION_ALIASES = {
    "expected behavior": "expected behaviour",
}


def validate_scenario(file_path: str) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Validates a benchmark scenario markdown file.

    Returns:
        Tuple of (is_valid: bool, errors: List[str], details: Dict[str, Any])
    """
    path = Path(file_path)
    errors: List[str] = []
    details: Dict[str, Any] = {}

    # 1. Missing File Check
    if not path.exists():
        errors.append(
            f"Error: Scenario file '{file_path}' not found.\n"
            f"  How to fix: Verify the file path or run 'evalrun init' to create a scenario file."
        )
        return False, errors, details

    if not path.is_file():
        errors.append(
            f"Error: Path '{file_path}' is a directory, not a scenario file.\n"
            f"  How to fix: Specify a single scenario Markdown file (.md)."
        )
        return False, errors, details

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        errors.append(
            f"Error: Could not read scenario file '{file_path}': {e}\n"
            f"  How to fix: Ensure the file is readable UTF-8 text."
        )
        return False, errors, details

    # 2. Frontmatter & YAML Validation
    if not content.startswith("---"):
        errors.append(
            f"Error: Malformed frontmatter in '{file_path}'. Missing opening '---' block header.\n"
            f"  How to fix: Ensure the file begins with '---' containing YAML metadata."
        )
        return False, errors, details

    try:
        metadata, body = parse_frontmatter(content)
    except Exception as e:
        errors.append(
            f"Error: Malformed YAML frontmatter in '{file_path}': {e}\n"
            f"  How to fix: Check your YAML syntax inside the '---' block for proper indenting and valid keys."
        )
        return False, errors, details

    if not isinstance(metadata, dict):
        errors.append(
            f"Error: Empty or non-dictionary frontmatter in '{file_path}'.\n"
            f"  How to fix: Provide YAML fields such as benchmark_id, name, and profile inside the '---' block."
        )
        return False, errors, details

    benchmark_id = metadata.get("benchmark_id") or metadata.get("id")
    if not benchmark_id:
        errors.append(
            f"Error: Missing required frontmatter field 'benchmark_id'.\n"
            f"  How to fix: Add 'benchmark_id: my-scenario-id' to the YAML frontmatter block."
        )

    name = metadata.get("name")
    if not name:
        errors.append(
            f"Error: Missing required frontmatter field 'name'.\n"
            f"  How to fix: Add 'name: My Scenario Name' to the YAML frontmatter block."
        )

    profile_name = str(metadata.get("profile", "travel-agent")).lower()
    details["benchmark_id"] = benchmark_id
    details["name"] = name
    details["profile"] = profile_name

    # 3. Profile Validation
    resolved_profile = PROFILE_REGISTRY.get(profile_name) or get_custom_profile(profile_name)
    if not resolved_profile:
        # Check case-insensitive registry keys
        for key, prof in PROFILE_REGISTRY.items():
            if key.lower() == profile_name:
                resolved_profile = prof
                break

    if not resolved_profile:
        available_profiles = ", ".join(sorted(list(PROFILE_REGISTRY.keys())))
        errors.append(
            f"Error: Unsupported profile '{profile_name}' in frontmatter.\n"
            f"  Available built-in profiles: {available_profiles}\n"
            f"  How to fix: Set 'profile: travel-agent' (or another valid profile) or register a custom profile using load_profile_from_file()."
        )
    else:
        details["pass_threshold"] = resolved_profile.pass_threshold
        details["weights"] = resolved_profile.weights

    # 4. Markdown Required Sections
    top_level_sections, subsections = _extract_heading_sections(body)
    normalized_sections = {}
    for raw_sec in top_level_sections.keys():
        norm_sec = raw_sec.lower().strip()
        norm_sec = SECTION_ALIASES.get(norm_sec, norm_sec)
        normalized_sections[norm_sec] = top_level_sections[raw_sec]

    for req_sec in REQUIRED_SECTIONS:
        if req_sec not in normalized_sections:
            errors.append(
                f"Error: Missing required section '# {req_sec.title()}' in scenario markdown.\n"
                f"  How to fix: Add a top-level header '# {req_sec.title()}' to your scenario file."
            )

    # 5. Evaluation Dimensions Validation
    details["dimensions"] = subsections

    if resolved_profile and subsections:
        profile_dim_names = {k.lower(): k for k in resolved_profile.weights.keys()}
        for dim in subsections:
            if dim.lower() not in profile_dim_names:
                valid_dims = ", ".join(list(resolved_profile.weights.keys()))
                errors.append(
                    f"Error: Evaluation dimension '{dim}' under '# Evaluation Criteria' is not supported by profile '{profile_name}'.\n"
                    f"  Supported dimensions for '{profile_name}': {valid_dims}\n"
                    f"  How to fix: Rename '### {dim}' header under '# Evaluation Criteria' to one of the supported dimensions."
                )
        present_dims = {dim.lower() for dim in subsections}
        for required_dim in resolved_profile.weights:
            if required_dim.lower() not in present_dims:
                errors.append(
                    f"Error: Missing evaluation dimension '{required_dim}' for profile '{profile_name}'.\n"
                    f"  How to fix: Add a '## {required_dim}' section under '# Evaluation Criteria'."
                )
    elif resolved_profile:
        for required_dim in resolved_profile.weights:
            errors.append(
                f"Error: Missing evaluation dimension '{required_dim}' for profile '{profile_name}'.\n"
                f"  How to fix: Add a '## {required_dim}' section under '# Evaluation Criteria'."
            )

    is_valid = len(errors) == 0
    return is_valid, errors, details


def _extract_heading_sections(markdown_body: str) -> Tuple[Dict[str, str], List[str]]:
    """Extracts top-level (#) sections and (###) dimension headers from markdown body."""
    top_level_sections: Dict[str, str] = {}
    eval_subsections: List[str] = []

    current_h1: Optional[str] = None
    h1_lines: List[str] = []

    for line in markdown_body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## ") and not stripped.startswith("### "):
            if current_h1:
                top_level_sections[current_h1] = "\n".join(h1_lines)
            current_h1 = stripped[2:].strip()
            h1_lines = []
        elif current_h1:
            h1_lines.append(line)
            if current_h1.lower() == "evaluation criteria" and (
                stripped.startswith("## ") or stripped.startswith("### ")
            ):
                prefix_length = 3 if stripped.startswith("## ") else 4
                sub_heading = stripped[prefix_length:].strip()
                if sub_heading and sub_heading not in eval_subsections:
                    eval_subsections.append(sub_heading)

    if current_h1:
        top_level_sections[current_h1] = "\n".join(h1_lines)

    return top_level_sections, eval_subsections
