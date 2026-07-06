"""Module for mapping parsed frontmatter and sections to a Benchmark dataclass."""

from typing import Any, Dict
from framework.exceptions import MapperError
from framework.models import Benchmark, ParsedBenchmark
from framework.parsers.transformers import parse_list, parse_nested_lists, parse_yaml_block


def map_to_benchmark(parsed_benchmark: ParsedBenchmark) -> Benchmark:
    """Maps a ParsedBenchmark (metadata + raw sections) to a Benchmark dataclass.

    Args:
        parsed_benchmark: The raw parsed benchmark components.

    Returns:
        A Benchmark dataclass instance.

    Raises:
        MapperError: If required metadata is missing or if transformations fail.
    """
    metadata = parsed_benchmark.metadata
    sections = parsed_benchmark.sections

    # 1. Validate and extract metadata
    benchmark_id = metadata.get("benchmark_id")
    if not benchmark_id:
        raise MapperError("Metadata is missing required field: 'benchmark_id'")
    if not isinstance(benchmark_id, str):
        raise MapperError("'benchmark_id' must be a string")

    name = metadata.get("name")
    if not name:
        raise MapperError("Metadata is missing required field: 'name'")
    if not isinstance(name, str):
        raise MapperError("'name' must be a string")

    # 2. Map and transform sections using the transformers module
    description = sections.description.strip()
    prompt = sections.prompt.strip()

    try:
        constraints = parse_yaml_block(sections.constraints)
    except Exception as e:
        raise MapperError(f"Failed to parse constraints YAML: {e}") from e

    expected_behavior = parse_list(sections.expected_behavior)
    evaluation_criteria = parse_nested_lists(sections.evaluation_criteria)
    pass_criteria = parse_list(sections.pass_criteria)
    failure_conditions = parse_list(sections.failure_conditions)

    notes = parse_list(sections.notes) if sections.notes else []
    profile = metadata.get("profile", "travel-agent")

    return Benchmark(
        benchmark_id=benchmark_id,
        name=name,
        description=description,
        prompt=prompt,
        constraints=constraints,
        expected_behavior=expected_behavior,
        evaluation_criteria=evaluation_criteria,
        pass_criteria=pass_criteria,
        failure_conditions=failure_conditions,
        notes=notes,
        profile=profile,
    )
