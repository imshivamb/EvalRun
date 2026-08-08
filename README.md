# Agent Evaluation Platform

An evaluation-first framework for building, benchmarking, and improving AI agents.

The first implementation is a travel planning agent, but the goal of this project is much broader: to build a reusable evaluation platform that can benchmark AI agents across different domains, models, and architectures.

> **Technical article:**  
> **My Reflection Loop Made Things Worse. My Evaluation Framework Showed Me Why.**  
> 🔗 https://shivambhardwaj.hashnode.dev/my-reflection-loop-made-things-worse-my-evaluation-framework-showed-me-why

---

## Why this project?

Most AI agent projects focus on building the agent.

I wanted to focus on evaluating it.

Instead of writing the planner first and testing it afterwards, I designed the benchmark scenarios before writing the agent itself. That meant the agent had to adapt to predefined evaluation criteria instead of the evaluation adapting to whatever the agent already did well.

The travel planner became the first system the platform evaluates.

---

## Features

- Multi-agent travel planning workflow
- Planner + Reflection architecture
- Session memory
- Research Agent
- Research Planner
- Benchmark evaluation framework
- Five benchmark scenarios
- Multi-model evaluation
- Reflection loop with approval threshold
- Mid-trip replanning
- Remote worker scheduling
- Route optimization
- Budget optimization
- Information gathering

---

## Benchmark Scenarios

The current evaluation suite includes five scenarios designed around real-world planning problems.

| Scenario | Focus |
|----------|-------|
| Budget | Constraint satisfaction and value optimization |
| Route Optimization | Geographic efficiency and backtracking |
| Remote Worker | Timezone-aware scheduling |
| Mid-trip Replanning | Localized adaptation and booking preservation |
| Information Gathering | Missing information detection and research quality |

Each benchmark includes predefined scoring criteria and pass/fail conditions.

---

## Architecture

```text
Planner
      │
      ▼
Reflection
      │
      ▼
Benchmark Evaluation
```

The reflection loop critiques planner outputs before they are evaluated.

Benchmark results determine whether changes actually improve the system rather than simply producing different outputs.

---

## Evaluation Philosophy

The central idea behind this project is simple:

> **Good evaluations are more important than good prompts.**

Without reliable benchmarks, it's difficult to know whether an agent is actually improving or simply generating different responses.

The evaluation framework is designed to expose regressions, constraint violations, and architectural weaknesses before they become production problems.

---

## Models Evaluated

Current benchmark runs include:

- GPT-5.6 Terra
- Gemini 3.1 Pro
- Gemini 3.5 Flash
- Llama 3.1 8B

---

## Quickstart & Running Benchmarks

### 1. Environment Setup

```bash
# Clone the repository
git clone https://github.com/imshivamb/agent-eval-platform.git
cd agent-eval-platform

# Setup virtual environment and dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Keys

Create a `.env` file in the root directory:

```env
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
NVIDIA_API_KEY=your_nvidia_key
OPENAI_MODEL=gpt-5.6-terra
```

### 3. Run Benchmark Suite

```bash
# Run multi-model comparison across all 5 benchmark scenarios
PYTHONPATH=. python3 runs/travel/compare_all.py

# Run unit test suite
PYTHONPATH=. python3 -m unittest discover -s tests -p "test_*.py"
```

---

## Roadmap

- ✅ Evaluation framework
- ✅ Reflection agent
- ✅ Session memory
- ✅ Multi-model benchmarking
- ✅ Benchmark reporting
- ✅ FastMCP deterministic validator integration
- 🚧 Live tool integrations
- 🚧 Additional agent domains
- 🚧 Interactive evaluation dashboard

---

## Tech Stack

- Python
- FastMCP
- OpenAI API
- Gemini API
- NVIDIA NIM (Llama 3.1 8B)
- Langfuse Observability
- Mermaid
- Markdown

---

## Documentation & Evaluation Findings

Benchmark reports and development logs are included in the repository:

- [Week 3 Evaluation Findings](results/week3/evaluation-findings.md)
- [Week 4 Multi-Model Comparison](results/week4/comparison.md)
- [Week 5 MCP Constraint Validation Findings](results/week5/mcp-validation-findings.md)
- [Evaluation Dashboard](dashboards/README.md)

---

## Feedback

I'm building this project in public as a way to learn more about AI evaluation and agent engineering.

If you have suggestions, ideas, or feedback, I'd genuinely love to hear them.