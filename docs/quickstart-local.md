# Local-Model Quick-Start Guide (`evalrun`)

This guide demonstrates evaluating an AI agent using locally hosted OpenAI-compatible model servers (vLLM, Ollama, LM Studio, or LocalAI) hosting models such as Qwen 2.5, Llama 3.3, or DeepSeek.

---

## 1. Local Server Responsibility

> **Note**: Users are responsible for launching, hosting, and securing their own local model endpoints before running `evalrun`.

### Example 1: Launching vLLM Server (Qwen 2.5 72B)
```bash
vllm serve Qwen/Qwen2.5-72B-Instruct \
  --port 8000 \
  --host 0.0.0.0
```

### Example 2: Launching Ollama Server (Llama 3.3)
```bash
ollama run llama3.3
# Exposes OpenAI-compatible endpoint at http://localhost:11434/v1
```

### Example 3: LM Studio
Start LM Studio local server on `http://localhost:1234/v1`.

---

## 2. Running Evaluation Against Local Endpoint

Run `evalrun` targeting local vLLM on `http://localhost:8000/v1` with `--api-key EMPTY`:

```bash
evalrun run \
  --scenario evals/scenarios/travel-agent/budget-constrained-itinerary.md \
  --agent agents.travel:TravelPlanningAgent \
  --model qwen2.5-72b-instruct \
  --base-url http://localhost:8000/v1 \
  --api-key EMPTY \
  --judge-model gpt-4o \
  --judge-base-url https://api.openai.com/v1 \
  --output results/local-qwen-run
```

---

## 3. Benefits of Local Model Evaluation

- **Zero API Costs**: Run hundreds of scenario iterations locally.
- **Data Privacy**: Prompts and generated agent plans never leave your local environment.
- **Latency Measurement**: Accurately profile local GPU inference throughput and latency in `report.html` and `manifest.json`.
