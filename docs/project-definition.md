# Agent Eval Platform

## Problem Statement

Recent advances in foundation models, agent frameworks, and AI-assisted development have significantly reduced the effort required to build AI agents. Today, developers can rapidly assemble functional agents using existing tools and APIs, making implementation more accessible than ever.

However, as building agents becomes easier, evaluating their quality has become a much harder problem. Most AI applications are still assessed thorugh subjective judegment... developers manually inspect outputs and decide whether they "look better". This approach does not provide a reliable or repeatable way to measure quality, compare different implementaions, or determine whether changes actually improve an agent's behavior.

As AI systems continue to evolve through model upgrades, prompt modifications, workflow changes, and new tools, objective evaluation becomes increasingly important. Without a consistent evaluation framework, teams risk introducing regressions, making decisions based on intuition rather than evidence, and shipping AI systems whose reliability cannot be measured.

This project addresses that problem by treating evaluation as a first-class component of the development process. Instead of building and AI agent first and adding evaluation later, the platform defines evaluation criteria, test scenarios, and measurable success metrics before the agent is implemented, enabling systematic iteration and continuous improvement.

## Goals

The primary goal of this project is to build a reusable evaluation framework for AI agents that enables systematic, repeatable, and measurable evaluation of agent behavior. Instead of relying on subjective evaluation scenarios and success criteria that can be used to assess how well an agent satisfies user requirements and task constraints.

The framework is designed to support continuous iteration by making it possible to compare different versions of an agent, identify regressions, and measure improvements over time. While the initial implementation focuses. on a travel-planning agent due to availability of real-world ground truth, the evaluation architecture is intentionally designed to be extensible so that additional agent types can be evaluated using the same framework in the future.

By separating the evaluation infrastructure from the agents themselves, the project aims to demonstrate an evaluation-first approach to AI system development, where objective measurement guides system improvement rather than subjective judgement.


## Non-Goals

This project is not intended to build the most capable travel-planning agent. The travel agent serves as a reference implementation used to validate the evaluation framework and its ability to measure agent behavior against predefined scenarios.

The initial version of the framework is not expected to support every category of AI agent. Instead, the project prioritizes validating the evaluation architecture within a single domain before extending it to additional agent types. Generalization is a long-term design goal rather than an initial implementation objective.

The project does not aim to develop or fine-tune foundation models, optimize model performance, or compare every available LLM. Those areas are intentionally excluded from the initial scope so the focus remains on building reliable evaluation infrastructure.

The primary objective is to design a reusable evaluation framework that enables systematic measurement, comparison, and continuous improvement of AI agents. Additional domains and capabilities will be added only after the core architecture has been validated.


## High-Level Architecture

The project is organized around a clear separation between evaluation infrastructure and the AI agents being evaluated.

The `framework/` directory contains the reusable evaluation infrastructure responsible for executing evaluation scenarios, scoring agent responses, tracking regressions, and producing measurable results. The framework is intentionally designed to remain independent of any specific AI agent or application domain, allowing the same evaluation logic to be reused across multiple agent implementations.

Evaluation scenarios are defined as structured data within the `evals/` directory rather than being embedded directly into application code. This separation allows new evaluation scenarios to be added, modified, or expanded without requiring changes to the evaluation framework itself, making the system easier to maintain and extend.

The `examples/` directory contains reference implementations of AI agents that are evaluated by the framework. The initial implementation focuses on a travel-planning agent due to the availability of real-world ground truth, but the architecture is designed so additional agent types can be introduced over time without modifying the core evaluation infrastructure.

Supporting directories such as `traces/` and `dashboards/` provide observability and historical performance tracking, enabling developers to compare different versions of an agent and identify regressions throughout the development lifecycle.
