# Phase 3 — Generic Evaluation Core & Model Adapters Specification

## Executive Summary

Phase 1 (MCP Reliability) and Phase 2 (Independent Auditor & Domain Generalization) established that multi-layer evaluation catches critical failure classes across domains. In Phase 3, we define a **Provider-Agnostic, Domain-Neutral Evaluation Core** that supports both cloud-hosted models (OpenAI, Gemini, NVIDIA NIM) and local user-hosted models (vLLM, Ollama, LM Studio for Qwen, Llama, DeepSeek).

This design enforces **Zero Breaking Changes**: existing agents (`TravelPlanningAgent`, `SupportTriageAgent`), evaluators, and benchmark runners continue working through compatibility properties and non-invasive wrappers.

---

## 1. Domain-Neutral Contracts (`framework/core/contracts.py`)

### A. `Scenario`
Domain-agnostic scenario specification with backward-compatibility properties for legacy `Benchmark` fields.

```python
@dataclass
class Scenario:
    id: str
    name: str
    domain: str  # e.g., "travel", "support_triage", "scheduling"
    description: str
    prompt: str
    constraints: Dict[str, Any]
    expected_behavior: List[str]
    evaluation_criteria: Dict[str, List[str]]
    pass_criteria: List[str]
    failure_conditions: List[str]
    notes: Optional[List[str]] = None
    profile_name: str = "travel-agent"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def benchmark_id(self) -> str:
        """Backward-compatibility alias for legacy code."""
        return self.id

    @property
    def profile(self) -> str:
        """Backward-compatibility alias for legacy profile name."""
        return self.profile_name
```

### B. `EvaluationSuite` (`framework/core/suite.py`)
Encapsulates a collection of scenarios and a map of evaluation profiles.

```python
@dataclass
class EvaluationSuite:
    suite_id: str
    name: str
    domain: str
    version: str
    scenarios: List[Scenario]
    profiles: Dict[str, EvaluationProfile]  # Maps profile_name -> EvaluationProfile

    def get_profile(self, profile_name: str) -> EvaluationProfile:
        return self.profiles.get(profile_name) or self.profiles["default"]
```

### C. `AgentAdapter` (`framework/core/adapters.py`)
Decouples agent evaluation from internal agent classes. Domain agents (`TravelPlanningAgent`, `SupportTriageAgent`) remain completely unchanged and are wrapped by adapter implementations.

```python
class AgentAdapter(ABC):
    @abstractmethod
    def run(self, scenario: Scenario, **kwargs) -> AgentOutput:
        """Executes the target agent on a scenario and returns standardized AgentOutput."""
        pass

class PythonAgentAdapter(AgentAdapter):
    """Wraps any in-process Python agent instance (e.g. TravelPlanningAgent)."""
    def __init__(self, agent: Any):
        self.agent = agent

    def run(self, scenario: Scenario, **kwargs) -> AgentOutput:
        return self.agent.run(scenario.prompt, **kwargs)

class HttpAgentAdapter(AgentAdapter):
    """Wraps an external REST API endpoint agent."""
    ...

class CliAgentAdapter(AgentAdapter):
    """Wraps a CLI binary agent."""
    ...
```

### D. `RunTrace` (`framework/core/trace.py`)
Instruments run execution metadata, timing, token counts, and error states.

```python
@dataclass
class RunTrace:
    trace_id: str
    scenario_id: str
    agent_id: str
    model_name: str
    started_at_utc: str
    finished_at_utc: str
    latency_seconds: float
    status: Literal["success", "error", "timeout"]
    error: Optional[str] = None
    retries_attempted: int = 0
    token_usage: Optional[Dict[str, int]] = None  # Optional: local endpoints may omit usage
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### E. `ModelAdapter` & Unified `OpenAICompatibleLLM` (`framework/llms/openai_compatible.py`)
A single provider-agnostic adapter class for hosted (OpenAI, NVIDIA NIM) and local user endpoints (vLLM, LM Studio, Ollama).

```python
class ModelAdapter(BaseLLM):
    """Abstract model adapter providing execution metadata on top of BaseLLM."""
    def __init__(self, provider: str, model_name: str, base_url: Optional[str] = None):
        self.provider = provider
        self.model_name = model_name
        self.base_url = base_url

class OpenAICompatibleLLM(ModelAdapter):
    """Universal OpenAI-compatible completion client."""
    def __init__(
        self,
        model_name: str,
        api_key: str = "EMPTY",
        base_url: Optional[str] = None,
        timeout: float = 180.0,
        extra_headers: Optional[Dict[str, str]] = None,
        provider: str = "openai_compatible",
    ):
        ...
```

---

## 2. Implementation Order

1. Add `framework/core/contracts.py` (with `Scenario`, `EvaluationSuite`, `RunTrace`).
2. Add compatibility conversion between `Benchmark` and `Scenario`.
3. Add `framework/core/adapters.py` (`PythonAgentAdapter`, `HttpAgentAdapter`, `CliAgentAdapter`).
4. Add `RunTrace` instrumentation to `BenchmarkRunner`.
5. Add `EvaluationSuite` loader in `framework/core/suite.py`.
6. Add `OpenAICompatibleLLM` in `framework/llms/openai_compatible.py`.
7. Add generic core & model adapter unit tests with mocked HTTP responses in `tests/test_generic_core.py` and `tests/test_openai_compatible.py`.
8. Verify all 58 existing unit tests pass cleanly.
