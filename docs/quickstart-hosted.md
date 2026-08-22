# Hosted-Model Quick-Start Guide (`evalrun`)

This guide demonstrates evaluating an AI agent against benchmark scenarios using cloud-hosted OpenAI-compatible APIs (OpenAI, NVIDIA NIM, or Gemini).

---

## 1. Prerequisites

Ensure your API key is exported in your environment:

```bash
export OPENAI_API_KEY="sk-proj-..."
```

For NVIDIA NIM or Gemini OpenAI-compatible endpoints:

```bash
export NVIDIA_API_KEY="nvapi-..."
```

---

## 2. Running Evaluation Against OpenAI GPT-5.6 Terra

Run evaluation on a benchmark scenario using GPT-5.6 Terra as both target model and judge model:

```bash
evalrun run \
  --scenario evals/scenarios/travel-agent/budget-constrained-itinerary.md \
  --agent agents.travel:TravelPlanningAgent \
  --model gpt-5.6-terra \
  --judge-model gpt-5.6-terra \
  --output results/hosted-gpt-5-6-terra-run
```

---

## 3. Running Evaluation Against Hosted NVIDIA NIM

To target Llama 3.3 70B hosted on NVIDIA NIM:

```bash
evalrun run \
  --scenario evals/scenarios/support-triage/urgent-ticket-escalation.md \
  --agent agents.support:SupportTriageAgent \
  --model meta/llama-3.3-70b-instruct \
  --base-url https://integrate.api.nvidia.com/v1 \
  --api-key $NVIDIA_API_KEY \
  --judge-model gpt-5.6-terra \
  --judge-base-url https://api.openai.com/v1 \
  --judge-api-key $OPENAI_API_KEY \
  --output results/hosted-nim-run
```

---

## 4. Generated Artifacts

Upon completion, `evalrun` generates:

1. `manifest.json`: Configuration details (API credentials auto-redacted).
2. `report.html`: Interactive, styled HTML report showing dimension scores, auditor gates, and run traces.
3. `*_report.json`: Detailed JSON score breakdown.
4. `{model}_{scenario}_itinerary.md`: Raw agent text output.
