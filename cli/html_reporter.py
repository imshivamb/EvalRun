"""HTML Report Generator for evalrun CLI."""

import html
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from framework.models import EvaluationResult


def generate_html_report(
    results: List[EvaluationResult],
    manifest: Dict[str, Any],
    output_dir: str,
    regression_report: Optional[Dict[str, Any]] = None,
) -> str:
    """Generates a standalone, beautifully styled interactive HTML evaluation report.

    Args:
        results: List of EvaluationResult objects.
        manifest: Redacted run configuration manifest dictionary.
        output_dir: Target output directory path.
        regression_report: Optional baseline comparison dictionary.

    Returns:
        Absolute path to the generated report.html file.
    """
    output_path = Path(output_dir) / "report.html"

    total_runs = len(results)
    passed_count = sum(1 for r in results if r.passed and getattr(r, "agent_metadata", {}).get("audit_gate_decision", "PASS") == "PASS")
    blocked_count = sum(1 for r in results if getattr(r, "agent_metadata", {}).get("audit_gate_decision") == "BLOCK")
    failed_count = total_runs - passed_count

    reg_detected = regression_report.get("regression_detected", False) if regression_report else False
    is_blocked = (regression_report.get("release_blocked", False) if regression_report else False) or (failed_count > 0) or (blocked_count > 0)

    avg_score = sum(r.overall_score for r in results) / total_runs if total_runs > 0 else 0.0

    # Top level verdict banner
    if is_blocked:
        verdict_class = "verdict-blocked"
        verdict_title = "RELEASE BLOCKED"
        verdict_sub = f"{failed_count} evaluator failure(s), {blocked_count} auditor block(s)"
        if reg_detected:
            verdict_sub += ", score regression detected against baseline"
    else:
        verdict_class = "verdict-approved"
        verdict_title = "RELEASE APPROVED"
        verdict_sub = "All evaluation thresholds, auditor gates, and baseline regression checks passed cleanly."

    reg_by_id = {}
    if regression_report:
        for s in regression_report.get("scenarios", []):
            reg_by_id[s["scenario_id"]] = s

    # Sort results fail/blocked first for human review
    def result_sort_key(res: EvaluationResult) -> int:
        gate = getattr(res, "agent_metadata", {}).get("audit_gate_decision", "PASS")
        is_reg = reg_by_id.get(res.benchmark_id, {}).get("is_regression", False)
        if is_reg or gate != "PASS" or not res.passed:
            return 0
        return 1

    sorted_results = sorted(results, key=result_sort_key)

    cards_html = []
    for res in sorted_results:
        meta = getattr(res, "agent_metadata", {})
        gate = meta.get("audit_gate_decision", "PASS")
        trace = meta.get("run_trace", {})
        audit = meta.get("audit_report", {})
        raw_output = meta.get("raw_content") or ""

        reg_info = reg_by_id.get(res.benchmark_id, {})
        is_reg = reg_info.get("is_regression", False)

        eval_badge_class = "badge-pass" if res.passed else "badge-fail"
        eval_status_str = "PASS" if res.passed else "FAIL"

        gate_badge_class = "badge-pass" if gate == "PASS" else "badge-block"
        gate_status_str = gate

        card_status_tag = "passed"
        if not res.passed:
            card_status_tag = "failed"
        elif gate != "PASS":
            card_status_tag = "blocked"
        elif is_reg:
            card_status_tag = "regressed"

        # Lowest scoring dimension
        lowest_dim = min(res.dimension_scores, key=lambda d: d.score) if res.dimension_scores else None
        lowest_dim_html = ""
        if lowest_dim:
            lowest_score_class = "score-high" if lowest_dim.score >= 80 else ("score-med" if lowest_dim.score >= 60 else "score-low")
            lowest_dim_html = f"""
            <div class="highlight-card">
                <strong>Lowest Dimension:</strong> {html.escape(lowest_dim.dimension)} 
                (<span class="{lowest_score_class}">{lowest_dim.score:.1f}/100</span>) — {html.escape(lowest_dim.reason[:120])}...
            </div>
            """

        # Baseline delta section
        baseline_delta_html = ""
        if reg_info:
            b_score = reg_info.get("baseline_score")
            c_score = reg_info.get("candidate_score")
            delta_val = reg_info.get("overall_delta")

            delta_class = "score-high" if (delta_val or 0) >= 0 else ("score-med" if (delta_val or 0) >= -5.0 else "score-low")
            delta_str = f"{delta_val:+.2f}" if delta_val is not None else "N/A"

            dim_delta_rows = []
            for dd in reg_info.get("dimension_deltas", []):
                dd_class = "score-high" if dd["delta"] >= 0 else ("score-med" if dd["delta"] >= -10.0 else "score-low")
                dim_delta_rows.append(f"""
                <tr>
                    <td>{html.escape(dd['dimension'])}</td>
                    <td>{dd['baseline_score']:.1f}</td>
                    <td>{dd['candidate_score']:.1f}</td>
                    <td><span class="{dd_class}">{dd['delta']:+.2f}</span></td>
                </tr>
                """)

            baseline_delta_html = f"""
            <div class="section-card baseline-card">
                <h3>Baseline Comparison Deltas</h3>
                <div class="delta-summary-grid">
                    <div><strong>Baseline Score:</strong> {b_score if b_score is not None else 'N/A'}</div>
                    <div><strong>Candidate Score:</strong> {c_score if c_score is not None else 'N/A'}</div>
                    <div><strong>Overall Delta:</strong> <span class="{delta_class}">{delta_str}</span></div>
                    <div><strong>Status:</strong> <code>{html.escape(str(reg_info.get('status')))}</code></div>
                </div>
                {f'<table class="data-table"><thead><tr><th>Dimension</th><th>Baseline</th><th>Candidate</th><th>Delta</th></tr></thead><tbody>{"".join(dim_delta_rows)}</tbody></table>' if dim_delta_rows else ''}
            </div>
            """

        dimension_rows = []
        for ds in res.dimension_scores:
            score_class = "score-high" if ds.score >= 80 else ("score-med" if ds.score >= 60 else "score-low")
            score_pct = max(0, min(100, ds.score))
            dimension_rows.append(f"""
            <tr>
                <td><strong>{html.escape(ds.dimension)}</strong></td>
                <td>
                    <div class="score-bar-container">
                        <div class="score-bar-fill" style="width: {score_pct}%;"></div>
                    </div>
                    <span class="{score_class}">{ds.score:.1f} / 100</span>
                </td>
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

        raw_output_section = ""
        if raw_output:
            raw_output_section = f"""
            <details class="raw-output-details">
                <summary>Inspect Raw Agent Output Text</summary>
                <pre class="raw-output-box">{html.escape(raw_output)}</pre>
            </details>
            """

        cards_html.append(f"""
        <div class="scenario-card" data-status="{card_status_tag}" data-name="{html.escape(res.benchmark_name.lower())}">
            <div class="scenario-header">
                <h2>{html.escape(res.benchmark_name)}</h2>
                <div class="badges">
                    <span class="badge {eval_badge_class}">Evaluator: {eval_status_str}</span>
                    <span class="badge {gate_badge_class}">Auditor: {gate_status_str}</span>
                    {f'<span class="badge badge-regressed">REGRESSED</span>' if is_reg else ''}
                    <span class="overall-score-pill">Score: {res.overall_score:.2f} / 100</span>
                </div>
            </div>

            {lowest_dim_html}
            {baseline_delta_html}
            {auditor_section}
            {trace_section}

            <div class="section-card">
                <h3>Dimension Breakdown</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th style="width: 25%;">Dimension</th>
                            <th style="width: 20%;">Score</th>
                            <th style="width: 55%;">LLM Judge Justification</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(dimension_rows)}
                    </tbody>
                </table>
            </div>

            {raw_output_section}
        </div>
        """)

    regressed_btn_html = '<button class="filter-btn" onclick="setFilter(\'regressed\', this)">Regressed</button>' if regression_report else ''

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
        .verdict-banner {{
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 24px;
            font-weight: 600;
        }}
        .verdict-blocked {{
            background: rgba(239, 68, 68, 0.15);
            border: 2px solid var(--fail-color);
            color: #fca5a5;
        }}
        .verdict-approved {{
            background: rgba(16, 185, 129, 0.15);
            border: 2px solid var(--pass-color);
            color: #6ee7b7;
        }}
        .verdict-banner h2 {{ margin: 0 0 4px 0; font-size: 22px; }}
        .verdict-banner p {{ margin: 0; font-size: 14px; opacity: 0.9; }}
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
        .controls-bar {{
            display: flex;
            gap: 16px;
            align-items: center;
            margin-bottom: 24px;
            flex-wrap: wrap;
        }}
        .search-input {{
            background: #1e293b;
            border: 1px solid var(--border-color);
            color: #fff;
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 14px;
            width: 260px;
        }}
        .filter-btn {{
            background: #1e293b;
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
        }}
        .filter-btn.active {{
            background: var(--accent-blue);
            color: #fff;
            border-color: var(--accent-blue);
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
        .badge-regressed {{ background: rgba(239, 68, 68, 0.3); color: #fca5a5; border: 1px solid var(--fail-color); }}
        .overall-score-pill {{
            background: var(--accent-blue);
            color: #fff;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
        }}
        .highlight-card {{
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid var(--block-color);
            border-radius: 6px;
            padding: 10px 14px;
            font-size: 13px;
            margin-bottom: 16px;
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
        .delta-summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
            margin-bottom: 12px;
            font-size: 14px;
        }}
        .score-bar-container {{
            background: #334155;
            height: 8px;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 4px;
            width: 100%;
        }}
        .score-bar-fill {{
            background: var(--accent-blue);
            height: 100%;
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
        .raw-output-details {{
            margin-top: 16px;
            background: #0f172a;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px;
        }}
        .raw-output-details summary {{
            cursor: pointer;
            font-weight: 600;
            color: var(--accent-blue);
        }}
        .raw-output-box {{
            margin-top: 12px;
            padding: 12px;
            background: #1e293b;
            border-radius: 6px;
            font-family: monospace;
            font-size: 12px;
            white-space: pre-wrap;
            word-break: break-word;
            max-height: 400px;
            overflow-y: auto;
        }}
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
        <div class="verdict-banner {verdict_class}">
            <h2>{verdict_title}</h2>
            <p>{verdict_sub}</p>
        </div>

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

        <div class="controls-bar">
            <input type="text" id="searchInput" class="search-input" placeholder="Search scenarios..." onkeyup="filterCards()">
            <button class="filter-btn active" onclick="setFilter('all', this)">All ({total_runs})</button>
            <button class="filter-btn" onclick="setFilter('passed', this)">Passed ({passed_count})</button>
            <button class="filter-btn" onclick="setFilter('failed', this)">Failed ({failed_count})</button>
            <button class="filter-btn" onclick="setFilter('blocked', this)">Blocked ({blocked_count})</button>
            {regressed_btn_html}
        </div>

        <div id="cardsContainer">
            {''.join(cards_html)}
        </div>

        <footer>
            Generated by evalrun Agent Evaluation Platform &bull; {html.escape(manifest.get('timestamp_utc', ''))}
        </footer>
    </div>

    <script>
        let currentFilter = 'all';
        function setFilter(filter, btn) {{
            currentFilter = filter;
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filterCards();
        }}
        function filterCards() {{
            const search = document.getElementById('searchInput').value.toLowerCase();
            const cards = document.querySelectorAll('.scenario-card');
            cards.forEach(card => {{
                const status = card.getAttribute('data-status');
                const name = card.getAttribute('data-name');
                const matchesFilter = (currentFilter === 'all') || (status === currentFilter);
                const matchesSearch = name.includes(search);
                if (matchesFilter && matchesSearch) {{
                    card.style.display = 'block';
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}
    </script>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return str(output_path)
