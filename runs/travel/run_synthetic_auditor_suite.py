"""Runner script to evaluate IndependentBudgetAuditor against 20 labeled synthetic test cases."""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

from agents.auditor import IndependentBudgetAuditor, FailureCode
from framework.llms.gemini import GeminiLLM
from framework.llms.openai import OpenAILLM


SUITE_PATH = "evals/synthetic_auditor_suite.json"
RESULTS_PATH = "results/multi-model-benchmarks/synthetic_auditor_results.json"


def load_env():
    """Loads environment variables from .env file."""
    if not os.path.exists(".env"):
        return
    for line in Path(".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ[key.strip()] = val.strip().strip('"').strip("'")


def create_auditor_llm():
    """Creates the LLM instance for the auditor."""
    model_name = os.environ.get("AUDITOR_MODEL") or os.environ.get("GEMINI_MODEL") or "models/gemini-3.1-pro-preview"
    if "gemini" in model_name.lower():
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        return GeminiLLM(model_name=model_name, api_key=api_key)
    else:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set.")
        return OpenAILLM(model_name=model_name, api_key=api_key)


def main():
    load_env()
    llm = create_auditor_llm()
    auditor = IndependentBudgetAuditor(llm=llm, max_retries=2)

    with open(SUITE_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    print(f"==================================================")
    print(f"RUNNING INDEPENDENT BUDGET AUDITOR SYNTHETIC SUITE")
    print(f"Auditor Model: {llm.model_name}")
    print(f"Total Test Cases: {len(cases)}")
    print(f"==================================================\n")

    results = []
    tp, fp, tn, fn = 0, 0, 0, 0
    total_latency_s = 0.0

    failure_code_counts = {code: {"total": 0, "detected": 0} for code in FailureCode.ALL_CODES}

    for idx, case in enumerate(cases, 1):
        case_id = case["id"]
        expected_status = case["ground_truth_status"]
        expected_violations = case["expected_violation_types"]

        for code in expected_violations:
            if code in failure_code_counts:
                failure_code_counts[code]["total"] += 1

        t0 = time.time()
        report = auditor.audit(
            scenario_prompt=case["scenario_prompt"],
            itinerary_content=case["itinerary_content"],
        )
        latency = time.time() - t0
        total_latency_s += latency

        actual_status = report.status
        detected_types = [v.violation_type for v in report.violations]

        # Check per-failure-code detection
        for code in expected_violations:
            if code in detected_types and code in failure_code_counts:
                failure_code_counts[code]["detected"] += 1

        # Classification logic
        is_tp = expected_status == "BLOCK" and actual_status == "BLOCK"
        is_tn = expected_status == "PASS" and actual_status == "PASS"
        is_fp = expected_status == "PASS" and actual_status == "BLOCK"
        is_fn = expected_status == "BLOCK" and actual_status == "PASS"

        if is_tp:
            tp += 1
            result_tag = "TRUE POSITIVE (Correct BLOCK)"
        elif is_tn:
            tn += 1
            result_tag = "TRUE NEGATIVE (Correct PASS)"
        elif is_fp:
            fp += 1
            result_tag = "FALSE POSITIVE (False Alarm BLOCK)"
        else:
            fn += 1
            result_tag = "FALSE NEGATIVE (Missed Violation PASS)"

        print(f"[{idx:02d}/{len(cases):02d}] {case_id:22s} | Expected: {expected_status:5s} | Actual: {actual_status:5s} | {latency:4.2f}s | {result_tag}")

        results.append({
            "id": case_id,
            "expected_status": expected_status,
            "actual_status": actual_status,
            "expected_violations": expected_violations,
            "detected_violations": detected_types,
            "classification": "TP" if is_tp else ("TN" if is_tn else ("FP" if is_fp else "FN")),
            "latency_seconds": round(latency, 2),
            "report": report.to_dict(),
        })

    # Summary Metrics Calculation
    total = len(cases)
    latencies = sorted([r["latency_seconds"] for r in results])
    p95_idx = int(0.95 * len(latencies)) if latencies else 0
    p95_latency = latencies[min(p95_idx, len(latencies) - 1)] if latencies else 0.0

    recall = (tp / (tp + fn) * 100.0) if (tp + fn) > 0 else 0.0
    specificity = (tn / (tn + fp) * 100.0) if (tn + fp) > 0 else 0.0
    precision = (tp / (tp + fp) * 100.0) if (tp + fp) > 0 else 0.0
    fp_rate = (fp / (tn + fp) * 100.0) if (tn + fp) > 0 else 0.0
    accuracy = ((tp + tn) / total * 100.0) if total > 0 else 0.0
    avg_latency = total_latency_s / total if total > 0 else 0.0

    print("\n==================== SYNTHETIC SUITE AUDIT REPORT ====================")
    print(f"Model Evaluated:               {llm.model_name}")
    print(f"Total Synthetic Cases:         {total}")
    print(f"True Positives (TP):           {tp}")
    print(f"True Negatives (TN):           {tn}")
    print(f"False Positives (FP):          {fp}")
    print(f"False Negatives (FN):          {fn}")
    print(f"----------------------------------------------------------------------")
    print(f"Auditor Sensitivity (Recall):  {recall:.2f}% (Target: >= 85%)")
    print(f"Auditor Specificity:           {specificity:.2f}% (Target: >= 90%)")
    print(f"False Positive Rate:           {fp_rate:.2f}% (Target: <= 10%)")
    print(f"Overall Gate Accuracy:         {accuracy:.2f}% (Target: >= 90%)")
    print(f"Average Latency per Audit:     {avg_latency:.2f}s (Target: <= 3.5s)")
    print(f"P95 Latency per Audit:         {p95_latency:.2f}s")
    print(f"----------------------------------------------------------------------")
    print("Per-Failure-Code Detection Rates:")
    for code, stats in failure_code_counts.items():
        tot = stats["total"]
        det = stats["detected"]
        rate = (det / tot * 100.0) if tot > 0 else 0.0
        print(f"  • {code:22s}: {det}/{tot} ({rate:.1f}%)")
    print("======================================================================\n")

    summary_data = {
        "auditor_model": llm.model_name,
        "total_cases": total,
        "confusion_matrix": {"TP": tp, "TN": tn, "FP": fp, "FN": fn},
        "metrics": {
            "recall_pct": round(recall, 2),
            "specificity_pct": round(specificity, 2),
            "precision_pct": round(precision, 2),
            "fp_rate_pct": round(fp_rate, 2),
            "accuracy_pct": round(accuracy, 2),
            "avg_latency_seconds": round(avg_latency, 2),
        },
        "failure_code_breakdown": failure_code_counts,
        "cases": results,
    }

    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    print(f"Saved audit summary dataset to: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
