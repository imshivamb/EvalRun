"""Structured JSON output parser and validator for AuditReport."""

import json
import re
from typing import Optional, Tuple, List, Dict, Any

from agents.auditor.schema import AuditReport, BudgetViolation, FailureCode


class AuditParser:
    """Parser and validator for Independent Budget Auditor LLM responses."""

    @staticmethod
    def parse_and_validate(text: str) -> Tuple[Optional[AuditReport], Optional[str]]:
        """Strictly parses and validates AuditReport from raw LLM output.

        Args:
            text: Raw response string from the model.

        Returns:
            Tuple of (AuditReport, None) on success, or (None, error_message) on failure.
        """
        try:
            # 1. Extract JSON block or brace contents
            match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
            if match:
                raw_json = match.group(1)
            else:
                match_brace = re.search(r"(\{.*\})", text, re.DOTALL)
                if match_brace:
                    raw_json = match_brace.group(1)
                else:
                    return None, "No JSON codeblock or object found in model output"

            # 2. Parse JSON syntax
            try:
                data = json.loads(raw_json)
            except Exception as ex:
                return None, f"JSON syntax error: {str(ex)}"

            if not isinstance(data, dict):
                return None, "Root JSON payload must be an object"

            # 3. Check mandatory keys
            required_keys = [
                "status",
                "audit_score",
                "violations",
                "total_estimated_spend_inr",
                "budget_limit_inr",
                "variance_inr",
                "audit_confidence",
                "reasoning_summary",
            ]
            missing_keys = [k for k in required_keys if k not in data]
            if missing_keys:
                return None, f"Missing required top-level JSON keys: {missing_keys}"

            # 4. Validate status
            status = str(data["status"]).upper().strip()
            if status not in ("PASS", "BLOCK"):
                return None, f"Invalid status '{data['status']}'; must be 'PASS' or 'BLOCK'"

            # 5. Validate numeric ranges
            try:
                audit_score = float(data["audit_score"])
                if not (0.0 <= audit_score <= 100.0):
                    return None, f"audit_score {audit_score} out of bounds [0.0, 100.0]"
            except (ValueError, TypeError):
                return None, "audit_score must be a numeric float"

            try:
                audit_confidence = float(data["audit_confidence"])
                if not (0.0 <= audit_confidence <= 1.0):
                    return None, f"audit_confidence {audit_confidence} out of bounds [0.0, 1.0]"
            except (ValueError, TypeError):
                return None, "audit_confidence must be a numeric float"

            # 6. Validate violations list and failure codes
            raw_violations = data["violations"]
            if not isinstance(raw_violations, list):
                return None, "'violations' must be a JSON array"

            violations: List[BudgetViolation] = []
            for idx, v in enumerate(raw_violations):
                if not isinstance(v, dict):
                    return None, f"violation at index {idx} must be an object"

                v_type = v.get("violation_type")
                if not v_type or v_type not in FailureCode.ALL_CODES:
                    return None, f"violation at index {idx} has invalid type '{v_type}'; must be one of {FailureCode.ALL_CODES}"

                description = v.get("description")
                if not description or not str(description).strip():
                    return None, f"violation at index {idx} is missing a description"

                try:
                    disc = float(v.get("estimated_discrepancy_inr", 0.0))
                except (ValueError, TypeError):
                    disc = 0.0

                affected_days = []
                if "affected_days" in v and isinstance(v["affected_days"], list):
                    for d in v["affected_days"]:
                        try:
                            affected_days.append(int(d))
                        except (ValueError, TypeError):
                            pass

                violations.append(
                    BudgetViolation(
                        violation_type=v_type,
                        description=str(description).strip(),
                        estimated_discrepancy_inr=disc,
                        affected_days=affected_days,
                    )
                )

            # 7. Validate Status vs Violations Consistency
            if status == "PASS" and len(violations) > 0:
                return None, f"Status is 'PASS' but violations array is non-empty ({len(violations)} violations specified)"
            if status == "BLOCK" and len(violations) == 0:
                return None, "Status is 'BLOCK' but violations array is empty (must list at least 1 violation)"

            return (
                AuditReport(
                    status=status,
                    audit_score=audit_score,
                    violations=violations,
                    total_estimated_spend_inr=float(data.get("total_estimated_spend_inr", 0.0)),
                    budget_limit_inr=float(data.get("budget_limit_inr", 0.0)),
                    variance_inr=float(data.get("variance_inr", 0.0)),
                    audit_confidence=audit_confidence,
                    reasoning_summary=str(data.get("reasoning_summary", "")),
                ),
                None,
            )
        except Exception as e:
            return None, f"Unexpected error parsing audit JSON: {str(e)}"
