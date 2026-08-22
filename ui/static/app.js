document.addEventListener('DOMContentLoaded', () => {
    const scenarioSelect = document.getElementById('scenario-select');
    const baselineSelect = document.getElementById('baseline-select');
    const evalForm = document.getElementById('eval-form');
    const runBtn = document.getElementById('run-btn');
    const btnText = document.getElementById('btn-text');
    const btnSpinner = document.getElementById('btn-spinner');

    const resultsCard = document.getElementById('results-card');
    const verdictBanner = document.getElementById('verdict-banner');
    const verdictTitle = document.getElementById('verdict-title');
    const verdictSub = document.getElementById('verdict-sub');
    const openReportBtn = document.getElementById('open-report-btn');
    const tableBody = document.getElementById('results-table-body');

    // 1. Fetch available scenarios
    fetch('/api/scenarios')
        .then(res => res.json())
        .then(data => {
            scenarioSelect.innerHTML = '';
            if (data.scenarios && data.scenarios.length > 0) {
                data.scenarios.forEach(sc => {
                    const opt = document.createElement('option');
                    opt.value = sc.path;
                    opt.textContent = `${sc.name} (${sc.path})`;
                    scenarioSelect.appendChild(opt);
                });
            } else {
                scenarioSelect.innerHTML = '<option value="">No scenarios found</option>';
            }
        })
        .catch(err => {
            scenarioSelect.innerHTML = '<option value="">Error loading scenarios</option>';
        });

    // 2. Fetch available baselines
    fetch('/api/baselines')
        .then(res => res.json())
        .then(data => {
            baselineSelect.innerHTML = '<option value="">None (Single Evaluation Run)</option>';
            if (data.baselines && data.baselines.length > 0) {
                data.baselines.forEach(b => {
                    const opt = document.createElement('option');
                    opt.value = b.path;
                    opt.textContent = `${b.run_id} (${b.path})`;
                    baselineSelect.appendChild(opt);
                });
            }
        })
        .catch(err => {
            console.error('Failed to load baselines', err);
        });

    // 3. Handle Form Submission
    evalForm.addEventListener('submit', (e) => {
        e.preventDefault();

        const scenario = scenarioSelect.value;
        const agent = document.getElementById('agent-spec').value.trim();
        const model = document.getElementById('target-model').value.trim();
        const base_url = document.getElementById('base-url').value.trim();
        const api_key = document.getElementById('api-key').value.trim();
        const baseline = baselineSelect.value;

        if (!scenario || !agent || !model) {
            alert('Please fill in all required fields.');
            return;
        }

        // Show loading spinner
        runBtn.disabled = true;
        btnText.textContent = 'Executing Evaluation...';
        btnSpinner.classList.remove('hidden');
        resultsCard.classList.add('hidden');

        const payload = {
            scenario,
            agent,
            model,
            base_url,
            api_key: api_key || undefined,
            baseline: baseline || undefined,
        };

        fetch('/api/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
            runBtn.disabled = false;
            btnText.textContent = 'Run Benchmark Evaluation';
            btnSpinner.classList.add('hidden');

            if (data.error) {
                alert(`Error: ${data.error}`);
                return;
            }

            renderResults(data);
        })
        .catch(err => {
            runBtn.disabled = false;
            btnText.textContent = 'Run Benchmark Evaluation';
            btnSpinner.classList.add('hidden');
            alert(`Execution failed: ${err.message}`);
        });
    });

    function renderResults(data) {
        resultsCard.classList.remove('hidden');
        tableBody.innerHTML = '';

        const isBlocked = data.release_blocked || !data.all_passed;

        if (isBlocked) {
            verdictBanner.className = 'verdict-banner verdict-blocked';
            verdictTitle.textContent = 'RELEASE BLOCKED';
            verdictSub.textContent = 'One or more scenarios failed evaluator thresholds, auditor gates, or baseline regressions.';
        } else {
            verdictBanner.className = 'verdict-banner verdict-approved';
            verdictTitle.textContent = 'RELEASE APPROVED';
            verdictSub.textContent = 'All benchmark scenarios passed quality thresholds and auditor release gates.';
        }

        if (data.html_report_path) {
            openReportBtn.href = data.html_report_path;
            openReportBtn.classList.remove('hidden');
        } else {
            openReportBtn.classList.add('hidden');
        }

        if (data.scenarios && data.scenarios.length > 0) {
            data.scenarios.forEach(sc => {
                const tr = document.createElement('tr');

                const nameTd = document.createElement('td');
                nameTd.textContent = sc.name || sc.benchmark_id;

                const scoreTd = document.createElement('td');
                scoreTd.innerHTML = `<strong>${sc.overall_score.toFixed(2)}</strong> / 100`;

                const evalTd = document.createElement('td');
                evalTd.innerHTML = sc.passed
                    ? '<span class="status-pill pill-pass">PASS</span>'
                    : '<span class="status-pill pill-block">FAIL</span>';

                const auditTd = document.createElement('td');
                auditTd.innerHTML = sc.auditor_gate === 'BLOCK'
                    ? '<span class="status-pill pill-block">BLOCK</span>'
                    : '<span class="status-pill pill-pass">PASS</span>';

                const statusTd = document.createElement('td');
                statusTd.innerHTML = (sc.passed && sc.auditor_gate !== 'BLOCK')
                    ? '<span class="status-pill pill-pass">APPROVED</span>'
                    : '<span class="status-pill pill-block">BLOCKED</span>';

                tr.appendChild(nameTd);
                tr.appendChild(scoreTd);
                tr.appendChild(evalTd);
                tr.appendChild(auditTd);
                tr.appendChild(statusTd);
                tableBody.appendChild(tr);
            });
        }
    }
});
