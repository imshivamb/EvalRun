"""HTML Report Generator for evalrun CLI."""

import html
import json
import os
from pathlib import Path
from typing import Any, Dict, List
from framework.models import EvaluationResult


def generate_html_report(results: List[EvaluationResult], manifest: Dict[str, Any], output_dir: str) -> str:
    """Generates a standalone, beautifully styled HTML evaluation report.

    Args:
        results: List of EvaluationResult objects.
        manifest: Redacted run configuration manifest dictionary.
        output_dir: Target output directory path.

    Returns:
        Absolute path to the generated report.html file.
    """
    output_path = Path(output_dir) / "report.html"

    total_runs = len(results)
    passed_count = sum(1 for r in results if r.passed and getattr(r, "agent_metadata", {}).get("audit_gate_decision", "PASS") == "PASS")
    blocked_count = sum(1 for r in results if getattr(r, "agent_metadata", {}).get("audit_gate_decision") == "BLOCK")
    failed_count = total_runs - passed_count

    avg_score = sum(r.overall_score for r in results) / total_runs if total_runs > 0 else 0.0

    cards_html = []
    for res in results:
        meta = getattr(res, "agent_metadata", {})
        gate = meta.get("audit_gate_decision", "PASS")
        trace = meta.get("run_trace", {})
        audit = meta.get("audit_report", {})

        eval_badge_class = "badge-pass" if res.passed else "badge-fail"
        eval_status_str = "PASS" if res.passed else "FAIL"

        gate_badge_class = "badge-pass" if gate == "PASS" else "badge-block"
        gate_status_str = gate

        dimension_rows = []
        for ds in res.dimension_scores:
            score_class = "score-high" if ds.score >= 80 else ("score-med" if ds.score >= 60 else "score-low")
            dimension_rows.append(f"""
            <tr>
                <td><strong>{html.escape(ds.dimension)}</strong></td>
                <td><span class="{score_class}">{ds.score:.1f} / 100</span></td>
                <td>{html.escape(ds.reason)}</td>
            </tr>
            """)

        auditor_section = ""
        if audit:
            violations_html = ""
            if audit.get("violations"):
                v_items = []
                for v in audit["violations"]:
                    v_items.append(f"""
                    <li>
                        <strong>[{html.escape(str(v.get('violation_type')))}]</strong>
                        {html.escape(str(v.get('description')))}
                        <span class="disc-amt">(Discrepancy: &#8377;{v.get('estimated_discrepancy_inr', 0):,.2f})</span>
                    </li>
                    """)
                violations_html = f"""
                <div class="violations-box">
                    <h4>Detected Budget Violations</h4>
                    <ul>{''.join(v_items)}</ul>
                </div>
                """

            auditor_section = f"""
            <div class="section-card auditor-card">
                <h3>Independent Budget Auditor Gate Report</h3>
                <div class="auditor-meta">
                    <p><strong>Gate Decision:</strong> <span class="{gate_badge_class}">{gate_status_str}</span></p>
                    <p><strong>Auditor Score:</strong> {audit.get('audit_score', 0.0):.2f} / 100</p>
                    <p><strong>Confidence:</strong> {audit.get('audit_confidence', 0.0):.2f}</p>
                    <p><strong>Reasoning:</strong> {html.escape(str(audit.get('reasoning_summary', 'N/A')))}</p>
                </div>
                {violations_html}
            </div>
            """

        trace_section = ""
        if trace:
            trace_section = f"""
            <div class="section-card trace-card">
                <h3>Execution Run Trace</h3>
                <table class="trace-table">
                    <tr><th>Trace ID</th><td><code>{html.escape(str(trace.get('trace_id', 'N/A')))}</code></td></tr>
                    <tr><th>Started (UTC)</th><td>{html.escape(str(trace.get('started_at_utc', 'N/A')))}</td></tr>
                    <tr><th>Finished (UTC)</th><td>{html.escape(str(trace.get('finished_at_utc', 'N/A')))}</td></tr>
                    <tr><th>Latency</th><td>{trace.get('latency_seconds', 0.0):.2f}s</td></tr>
                    <tr><th>Status</th><td><code>{html.escape(str(trace.get('status', 'N/A')))}</code></td></tr>
                </table>
            </div>
            """

        cards_html.append(f"""
        <div class="scenario-card">
            <div class="scenario-header">
                <h2>{html.escape(res.benchmark_name)}</h2>
                <div class="badges">
                    <span class="badge {eval_badge_class}">Evaluator: {eval_status_str}</span>
                    <span class="badge {gate_badge_class}">Auditor: {gate_status_str}</span>
                    <span class="overall-score-pill">Score: {res.overall_score:.2f} / 100</span>
                </div>
            </div>

            {auditor_section}
            {trace_section}

            <div class="section-card">
                <h3>Dimension Breakdown</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th style="width: 25%;">Dimension</th>
                            <th style="width: 15%;">Score</th>
                            <th style="width: 60%;">LLM Judge Justification</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(dimension_rows)}
                    </tbody>
                </table>
            </div>
        </div>
        """)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>evalrun Evaluation Report — {html.escape(manifest.get('run_id', 'N/A'))}</title>
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border-color: #334155;
            --pass-color: #10b981;
            --fail-color: #ef4444;
            --block-color: #f59e0b;
            --accent-blue: #3b82f6;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 24px;
            line-height: 1.5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        header {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }}
        h1 {{
            margin: 0 0 12px 0;
            font-size: 24px;
            color: #ffffff;
        }}
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-top: 16px;
        }}
        .meta-item {{
            background: #0f172a;
            padding: 12px 16px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }}
        .meta-label {{
            font-size: 12px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .meta-val {{
            font-size: 16px;
            font-weight: 600;
            margin-top: 4px;
            word-break: break-all;
        }}
        .scenario-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }}
        .scenario-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 16px;
            margin-bottom: 20px;
        }}
        .scenario-header h2 {{
            margin: 0;
            font-size: 20px;
        }}
        .badges {{
            display: flex;
            gap: 8px;
            align-items: center;
        }}
        .badge {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
        }}
        .badge-pass {{ background: rgba(16, 185, 129, 0.2); color: var(--pass-color); border: 1px solid var(--pass-color); }}
        .badge-fail {{ background: rgba(239, 68, 68, 0.2); color: var(--fail-color); border: 1px solid var(--fail-color); }}
        .badge-block {{ background: rgba(245, 158, 11, 0.2); color: var(--block-color); border: 1px solid var(--block-color); }}
        .overall-score-pill {{
            background: var(--accent-blue);
            color: #fff;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
        }}
        .section-card {{
            background: #0f172a;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
        }}
        .section-card h3 {{
            margin-top: 0;
            font-size: 16px;
            color: var(--text-muted);
        }}
        table.data-table, table.trace-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 12px;
        }}
        table.data-table th, table.data-table td, table.trace-table th, table.trace-table td {{
            text-align: left;
            padding: 10px 12px;
            border-bottom: 1px solid var(--border-color);
        }}
        table.data-table th {{
            color: var(--text-muted);
            font-size: 13px;
        }}
        .score-high {{ color: var(--pass-color); font-weight: 600; }}
        .score-med {{ color: var(--block-color); font-weight: 600; }}
        .score-low {{ color: var(--fail-color); font-weight: 600; }}
        .violations-box {{
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid var(--fail-color);
            border-radius: 6px;
            padding: 12px 16px;
            margin-top: 12px;
        }}
        .violations-box h4 {{ margin: 0 0 8px 0; color: var(--fail-color); }}
        .violations-box ul {{ margin: 0; padding-left: 20px; }}
        .disc-amt {{ color: var(--block-color); font-size: 13px; }}
        code {{
            background: #1e293b;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: monospace;
        }}
        footer {{
            text-align: center;
            color: var(--text-muted);
            font-size: 12px;
            margin-top: 40px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>evalrun Benchmark Evaluation Report</h1>
            <div class="meta-grid">
                <div class="meta-item">
                    <div class="meta-label">Run ID</div>
                    <div class="meta-val">{html.escape(manifest.get('run_id', 'N/A'))}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Target Model</div>
                    <div class="meta-val">{html.escape(manifest.get('target_model', {}).get('model_name', 'N/A'))}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Judge Model</div>
                    <div class="meta-val">{html.escape(manifest.get('judge_model', {}).get('model_name', 'N/A'))}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Average Score</div>
                    <div class="meta-val">{avg_score:.2f} / 100</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Pass / Fail / Block</div>
                    <div class="meta-val">{passed_count} / {failed_count} / {blocked_count}</div>
                </div>
            </div>
        </header>

        {''.join(cards_html)}

        <footer>
            Generated by evalrun Agent Evaluation Platform &bull; {html.escape(manifest.get('timestamp_utc', ''))}
        </footer>
    </div>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return str(output_path)
