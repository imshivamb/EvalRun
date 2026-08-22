"""Custom Evaluation Profiles and Evaluators Plugin Registry."""

import json
from pathlib import Path
from typing import Dict, Optional
from framework.models import EvaluationProfile


_DYNAMIC_PROFILE_REGISTRY: Dict[str, EvaluationProfile] = {}


def register_profile(name: str, profile: EvaluationProfile) -> None:
    """Registers a custom evaluation profile into the global profile registry."""
    _DYNAMIC_PROFILE_REGISTRY[name.lower()] = profile


def get_custom_profile(name: str) -> Optional[EvaluationProfile]:
    """Retrieves a registered profile by name."""
    return _DYNAMIC_PROFILE_REGISTRY.get(name.lower())


def load_profile_from_file(filepath: str) -> EvaluationProfile:
    """Loads an EvaluationProfile from a JSON configuration file."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Custom profile file '{filepath}' not found.")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    profile_id = data.get("profile_id") or path.stem
    name = data.get("name", profile_id)
    pass_threshold = float(data.get("pass_threshold", 75.0))

    raw_weights = data.get("dimension_weights") or data.get("weights") or {}
    weights: Dict[str, float] = {}
    if isinstance(raw_weights, list):
        for item in raw_weights:
            if isinstance(item, dict) and "dimension" in item:
                weights[item["dimension"]] = float(item.get("weight", 1.0))
    elif isinstance(raw_weights, dict):
        weights = {str(k): float(v) for k, v in raw_weights.items()}

    profile = EvaluationProfile(
        name=name,
        weights=weights,
        pass_threshold=pass_threshold,
    )

    register_profile(profile_id, profile)
    return profile
