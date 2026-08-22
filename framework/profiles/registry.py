"""Custom Evaluation Profiles and Evaluators Plugin Registry."""

import importlib
import json
from pathlib import Path
from typing import Any, Dict, Optional
from framework.evaluation.base import BaseEvaluator
from framework.models import EvaluationProfile


_DYNAMIC_PROFILE_REGISTRY: Dict[str, EvaluationProfile] = {}
_DYNAMIC_EVALUATOR_REGISTRY: Dict[str, BaseEvaluator] = {}


def register_profile(name: str, profile: EvaluationProfile) -> None:
    """Registers a custom evaluation profile into the global profile registry."""
    _DYNAMIC_PROFILE_REGISTRY[name.lower()] = profile


def get_custom_profile(name: str) -> Optional[EvaluationProfile]:
    """Retrieves a registered profile by name."""
    return _DYNAMIC_PROFILE_REGISTRY.get(name.lower())


def register_evaluator_plugin(dimension_name: str, evaluator: BaseEvaluator) -> None:
    """Registers a custom evaluator plugin for a dimension name."""
    _DYNAMIC_EVALUATOR_REGISTRY[dimension_name] = evaluator
    _DYNAMIC_EVALUATOR_REGISTRY[dimension_name.lower()] = evaluator


def get_evaluator_plugin(dimension_name: str) -> Optional[BaseEvaluator]:
    """Retrieves a registered custom evaluator plugin by dimension name."""
    return _DYNAMIC_EVALUATOR_REGISTRY.get(dimension_name) or _DYNAMIC_EVALUATOR_REGISTRY.get(dimension_name.lower())


def load_evaluator_plugin_from_spec(spec: str, judge_llm: Any = None) -> BaseEvaluator:
    """Dynamically loads and instantiates a custom evaluator plugin from a specifier.

    Args:
        spec: Import specifier string ('module:Class' or 'module:factory').
        judge_llm: Optional judge LLM instance to pass to the evaluator constructor.

    Returns:
        Instantiated BaseEvaluator.
    """
    if ":" not in spec:
        raise ValueError(f"Invalid evaluator specifier '{spec}'. Expected 'module:Class' or 'module:factory'.")

    mod_name, attr_name = spec.split(":", 1)
    module = importlib.import_module(mod_name)
    target = getattr(module, attr_name)

    if inspect_is_class(target):
        try:
            return target(llm=judge_llm)
        except TypeError:
            try:
                return target(judge_llm=judge_llm)
            except TypeError:
                return target()
    elif callable(target):
        try:
            return target(llm=judge_llm)
        except TypeError:
            return target()
    else:
        raise ValueError(f"Evaluator specifier '{spec}' resolved to non-callable object.")


def inspect_is_class(obj: Any) -> bool:
    import inspect
    return inspect.isclass(obj)


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
