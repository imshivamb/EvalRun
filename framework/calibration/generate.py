"""Generate remaining unique calibration outputs by running agents, not judges."""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from framework.calibration.harvest import (
    DIVERSITY_BUCKETS,
    SCENARIO_PROFILES,
    HarvestedRecord,
    index_scenarios,
)
from framework.calibration.schema import content_sha256, make_case_id
from framework.calibration.store import rebuild_manifest, write_corpus

AgentRunner = Callable[[str, str], str]
MAX_DUPLICATE_ATTEMPTS = 3
TARGET_MIN_DEFAULT = 40
TARGET_MAX_DEFAULT = 60


def extract_user_prompt(markdown: str) -> str:
    """Return the User Prompt section without requiring a full benchmark parse."""
    capturing = False
    collected: List[str] = []
    for line in markdown.splitlines():
        if line.startswith("# ") and capturing:
            break
        if line.strip() == "# User Prompt":
            capturing = True
            continue
        if capturing:
            collected.append(line)
    prompt = "\n".join(collected).strip()
    if not prompt:
        raise ValueError("Scenario markdown is missing a User Prompt section.")
    return prompt


def pick_next_scenario(
    diversity_counts: Dict[str, int],
    unique_count: int,
    *,
    target_min: int,
    target_max: int,
    blocked: Set[str],
) -> Optional[str]:
    """Prefer empty diversity buckets; never pad Budget when a required scenario failed."""
    if unique_count >= target_max:
        return None
    floor_met = all(count >= 1 for count in diversity_counts.values())
    if unique_count >= target_min and floor_met:
        return None
    for scenario_id, bucket in DIVERSITY_BUCKETS.items():
        if scenario_id in blocked:
            continue
        if diversity_counts.get(bucket, 0) < 1:
            return scenario_id
    if floor_met and unique_count < target_min:
        return min(
            (sid for sid in DIVERSITY_BUCKETS if sid not in blocked),
            key=lambda sid: (diversity_counts[DIVERSITY_BUCKETS[sid]], sid),
            default=None,
        )
    return None


def generate_cases(
    dest: Path,
    scenarios_root: Path,
    run_agent: AgentRunner,
    generator_model: str,
    target_min: int = TARGET_MIN_DEFAULT,
    target_max: int = TARGET_MAX_DEFAULT,
) -> Dict[str, Any]:
    """Append unique generated outputs until the corpus gate is met or a scenario fails."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    scenario_files = index_scenarios(scenarios_root)
    seen = _existing_hashes(dest)
    manifest = rebuild_manifest(dest)
    diversity_counts = dict(manifest["diversity_counts"])
    unique_count = int(manifest["unique_count"])
    blocked: Set[str] = set()
    failed_scenarios: List[str] = []
    duplicate_attempts: Dict[str, int] = {}
    seq = _generated_count(dest)

    while True:
        scenario_id = pick_next_scenario(
            diversity_counts,
            unique_count,
            target_min=target_min,
            target_max=target_max,
            blocked=blocked,
        )
        if scenario_id is None:
            break
        scenario_path = scenario_files.get(scenario_id)
        if scenario_path is None:
            failed_scenarios.append(scenario_id)
            blocked.add(scenario_id)
            if diversity_counts[DIVERSITY_BUCKETS[scenario_id]] < 1:
                break
            continue
        prompt = extract_user_prompt(scenario_path.read_text(encoding="utf-8"))
        try:
            output_text = run_agent(scenario_id, prompt)
        except Exception:
            failed_scenarios.append(scenario_id)
            blocked.add(scenario_id)
            if diversity_counts[DIVERSITY_BUCKETS[scenario_id]] < 1:
                break
            continue
        if not isinstance(output_text, str) or not output_text.strip():
            failed_scenarios.append(scenario_id)
            blocked.add(scenario_id)
            if diversity_counts[DIVERSITY_BUCKETS[scenario_id]] < 1:
                break
            continue
        digest = content_sha256(output_text)
        if digest in seen:
            duplicate_attempts[scenario_id] = duplicate_attempts.get(scenario_id, 0) + 1
            if duplicate_attempts[scenario_id] >= MAX_DUPLICATE_ATTEMPTS:
                failed_scenarios.append(scenario_id)
                blocked.add(scenario_id)
                if diversity_counts[DIVERSITY_BUCKETS[scenario_id]] < 1:
                    break
            continue
        seq += 1
        model_slug = generator_model.replace("/", "-").replace(".", "-")
        source_tag = f"generated-{model_slug}-{seq:03d}"
        record = HarvestedRecord(
            case_id=make_case_id(scenario_id, source_tag, digest),
            scenario_id=scenario_id,
            profile=SCENARIO_PROFILES.get(scenario_id, "travel-agent"),
            source_tag=source_tag,
            source_path=f"generated:{generator_model}",
            generator_model=generator_model,
            harvested_judge_overall=None,
            output_text=output_text,
            content_sha256=digest,
            source="generated",
        )
        write_corpus([record], dest, scenarios_root=scenarios_root)
        seen.add(digest)
        diversity_counts[DIVERSITY_BUCKETS[scenario_id]] += 1
        unique_count += 1

    result = rebuild_manifest(dest)
    result["failed_scenarios"] = failed_scenarios
    return result


def _existing_hashes(dest: Path) -> Set[str]:
    hashes: Set[str] = set()
    cases_root = dest / "cases"
    if not cases_root.exists():
        return hashes
    for output_path in cases_root.glob("*/output.md"):
        hashes.add(content_sha256(output_path.read_text(encoding="utf-8")))
    return hashes


def _generated_count(dest: Path) -> int:
    cases_root = dest / "cases"
    if not cases_root.exists():
        return 0
    count = 0
    for meta_path in cases_root.glob("*/meta.json"):
        meta = meta_path.read_text(encoding="utf-8")
        if '"source": "generated"' in meta:
            count += 1
    return count
