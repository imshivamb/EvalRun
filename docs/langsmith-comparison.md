# LangSmith vs. Agent Evaluation Platform (`evalrun`) Comparison

## Architectural Paradigm Comparison

| Dimension | LangSmith (Hosted SaaS Platform) | Agent Evaluation Platform (`evalrun`) |
| :--- | :--- | :--- |
| **Deployment Model** | Hosted SaaS / Multi-tenant Cloud Platform | Local-First, Zero-Server Command Line & Python SDK |
| **Data Privacy & Secrets** | Prompts, LLM outputs, traces & keys sent to cloud | 100% Local-First. Secrets auto-redacted in local JSON/HTML |
| **Primary Differentiator** | Broad production observability, feedback & dataset curation | **Independent Budget Auditor Gate** + **Score Regression Release Gates** |
| **Release Decision Contract** | Soft quality feedback & dataset scoring | Hard Exit Codes (`0` Approved, `1` Blocked, `2` Runtime Error) |
| **Local / Offline Execution** | Requires active internet connection to cloud API | Fully usable offline (with local vLLM / Ollama endpoints) |
| **Infrastructure Cost** | Per-token / trace SaaS subscription fees | Zero platform fees (local execution or direct provider API cost only) |

---

## Where `evalrun` Differentiates

1. **Quality Score $\neq$ Release Decision**:
   LangSmith evaluators score datasets on qualitative metrics (e.g. correctness 0.85). In contrast, `evalrun` pairs qualitative LLM judges with an **Independent Budget Auditor** enforcing hard mathematical, policy, and financial constraints (e.g. blocking unbudgeted baggage lockers or currency hallucinations even if qualitative score is 95/100).
2. **Automated Baseline Regression Release Gates**:
   `evalrun` calculates per-scenario and per-dimension score deltas ($\Delta \text{score}$) against stored baseline runs, blocking CI/CD pipelines (Exit Code `1`) when score regressions exceed `--max-regression`.
3. **Local HTML Human Review Layer**:
   Produces self-contained, interactive `report.html` files with failure quick-jump bars, auto-opened failing cards, visual score progress bars, and embedded raw model output text—ready for local inspection or GitHub Actions artifact uploads.

---

## Where `evalrun` Intentionally Remains Narrower

`evalrun` is explicitly designed as a developer evaluation and regression testing toolkit for Applied AI engineering. It intentionally refrains from providing:

- Multi-tenant cloud hosting or SaaS user accounts
- Online production monitoring dashboards or user feedback collection webhooks
- Managed GPU hosting or LLM provider proxy billing
- Complex UI collaboration layers
