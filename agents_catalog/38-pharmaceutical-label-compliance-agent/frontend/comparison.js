/* Evaluation Comparison Module */
const Comparison = (function () {
  let _originalResultsHTML = null;
  let _currentComparisonIds = null;
  let _currentSwapped = false;

  function shouldShowCompareButton(project) {
    return project &&
      Array.isArray(project.evaluations) &&
      project.evaluations.length >= 2;
  }

  function diffViolations(baselineViolations, comparisonViolations) {
    const baseline = baselineViolations || [];
    const comparison = comparisonViolations || [];
    const baselineTitles = new Set(baseline.map(v => v.title));
    const comparisonTitles = new Set(comparison.map(v => v.title));

    return {
      new: comparison.filter(v => !baselineTitles.has(v.title)),
      resolved: baseline.filter(v => !comparisonTitles.has(v.title)),
      unchanged: comparison.filter(v => baselineTitles.has(v.title))
    };
  }

  function startComparison(evalId1, evalId2, swapped) {
    const evaluations = currentProject.evaluations || [];
    const evalA = evaluations.find(e => e.id === evalId1);
    const evalB = evaluations.find(e => e.id === evalId2);
    if (!evalA || !evalB) return;

    // Determine labels based on position in evaluations array
    const indexA = evaluations.indexOf(evalA);
    const indexB = evaluations.indexOf(evalB);
    const labelA = indexA === 0 ? 'Latest' : '#' + (evaluations.length - indexA);
    const labelB = indexB === 0 ? 'Latest' : '#' + (evaluations.length - indexB);

    // Default: older is baseline, newer is comparison. If swapped, reverse.
    let baseline, comparison, baselineLabel, comparisonLabel;
    if (!swapped) {
      [baseline, comparison] = new Date(evalA.timestamp) <= new Date(evalB.timestamp)
        ? [evalA, evalB] : [evalB, evalA];
      [baselineLabel, comparisonLabel] = new Date(evalA.timestamp) <= new Date(evalB.timestamp)
        ? [labelA, labelB] : [labelB, labelA];
    } else {
      [baseline, comparison] = new Date(evalA.timestamp) <= new Date(evalB.timestamp)
        ? [evalB, evalA] : [evalA, evalB];
      [baselineLabel, comparisonLabel] = new Date(evalA.timestamp) <= new Date(evalB.timestamp)
        ? [labelB, labelA] : [labelA, labelB];
    }

    // Store current comparison state for swap
    _currentComparisonIds = [evalId1, evalId2];
    _currentSwapped = !!swapped;

    const resultsSection = document.getElementById('resultsSection');
    if (!resultsSection) return;

    // Only store original HTML on the first comparison entry, not on swaps
    if (!_originalResultsHTML) {
      _originalResultsHTML = resultsSection.innerHTML;
    }

    const scoreA = baseline.complianceScore != null ? baseline.complianceScore : '--';
    const scoreB = comparison.complianceScore != null ? comparison.complianceScore : '--';
    const diff = (typeof scoreA === 'number' && typeof scoreB === 'number')
      ? scoreB - scoreA
      : null;

    const diffDisplay = diff != null
      ? `<span class="comparison-diff ${diff >= 0 ? 'positive' : 'negative'}">${diff >= 0 ? '+' : ''}${diff}%</span>`
      : '';

    const violationsA = baseline.formattedViolations || [];
    const violationsB = comparison.formattedViolations || [];
    const violationDiff = diffViolations(violationsA, violationsB);

    const dateA = new Date(baseline.timestamp).toLocaleDateString();
    const dateB = new Date(comparison.timestamp).toLocaleDateString();

    const imgA = baseline.annotatedImageUrl || '';
    const imgB = comparison.annotatedImageUrl || '';

    setSafeHTML(resultsSection, buildComparisonHTML({
      dateA, dateB, imgA, imgB,
      scoreA, scoreB, diffDisplay,
      violationDiff,
      baselineLabel, comparisonLabel
    }));
  }

  function buildComparisonHTML(data) {
    const { dateA, dateB, imgA, imgB, scoreA, scoreB, diffDisplay, violationDiff, baselineLabel, comparisonLabel } = data;

    const violationRows = [
      ...violationDiff.new.map(v => renderViolationRow(v, 'new', 'NEW')),
      ...violationDiff.resolved.map(v => renderViolationRow(v, 'resolved', 'RESOLVED')),
      ...violationDiff.unchanged.map(v => renderViolationRow(v, 'unchanged', 'UNCHANGED'))
    ].join('');

    return `
      <div class="comparison-container">
        <div class="comparison-header">
          <h3>Evaluation Comparison</h3>
          <div class="comparison-header-actions">
            <button class="btn-swap-comparison" data-click="swapComparison" aria-label="Swap baseline and comparison">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"/>
              </svg>
              Swap
            </button>
            <button class="btn-exit-comparison" data-click="exitComparison" aria-label="Exit comparison view">
              Exit Comparison
            </button>
          </div>
        </div>

        <div class="comparison-images">
          <div class="comparison-image-panel">
            <div class="comparison-score-label" style="padding:0.75rem 1rem;font-weight:700;">Baseline (${escapeHtml(baselineLabel)}) — ${escapeHtml(dateA)}</div>
            ${imgA
              ? `<img src="${escapeHtml(imgA)}" alt="Baseline evaluation annotated label">`
              : '<div style="padding:2rem;text-align:center;color:var(--text-muted);">Image unavailable</div>'}
          </div>
          <div class="comparison-image-panel">
            <div class="comparison-score-label" style="padding:0.75rem 1rem;font-weight:700;">Comparison (${escapeHtml(comparisonLabel)}) — ${escapeHtml(dateB)}</div>
            ${imgB
              ? `<img src="${escapeHtml(imgB)}" alt="Comparison evaluation annotated label">`
              : '<div style="padding:2rem;text-align:center;color:var(--text-muted);">Image unavailable</div>'}
          </div>
        </div>

        <div class="comparison-score-diff">
          <div class="comparison-score">
            <div class="comparison-score-value">${typeof scoreA === 'number' ? Number(scoreA) + '%' : escapeHtml(String(scoreA))}</div>
            <div class="comparison-score-label">Baseline (${escapeHtml(baselineLabel)})</div>
          </div>
          <div class="comparison-arrow">→</div>
          <div class="comparison-score">
            <div class="comparison-score-value">${typeof scoreB === 'number' ? Number(scoreB) + '%' : escapeHtml(String(scoreB))}</div>
            <div class="comparison-score-label">Comparison (${escapeHtml(comparisonLabel)})</div>
          </div>
          ${diffDisplay ? `<div>${diffDisplay}</div>` : ''}
        </div>

        <div class="comparison-violations">
          ${violationRows || '<p style="text-align:center;color:var(--text-muted);padding:1rem;">No violations to compare.</p>'}
        </div>
      </div>`;
  }

  function renderViolationRow(violation, type, label) {
    const badgeClass = type;
    const resolvedClass = type === 'resolved' ? ' resolved' : '';
    return `
      <div class="violation-item ${escapeHtml(violation.severity || '')}${resolvedClass}">
        <div class="violation-header">
          <div class="violation-title">${escapeHtml(violation.title)}</div>
          <span class="comparison-badge ${badgeClass}">${label}</span>
        </div>
        <div class="violation-description">${escapeHtml(violation.description || '')}</div>
      </div>`;
  }

  function exitComparison() {
    const resultsSection = document.getElementById('resultsSection');
    if (!resultsSection || !_originalResultsHTML) return;
    setSafeHTML(resultsSection, _originalResultsHTML);
    _originalResultsHTML = null;
    _currentComparisonIds = null;
    _currentSwapped = false;
    // Re-render the normal view
    if (typeof loadResults === 'function') {
      loadResults();
    }
  }

  function swapComparison() {
    if (!_currentComparisonIds || _currentComparisonIds.length !== 2) return;
    // Re-run comparison with swapped flag toggled
    startComparison(_currentComparisonIds[0], _currentComparisonIds[1], !_currentSwapped);
  }

  function renderCompareButton(container) {
    if (!container) return;
    if (!shouldShowCompareButton(currentProject)) {
      container.replaceChildren();
      return;
    }

    const evaluations = currentProject.evaluations || [];

    setSafeHTML(container, `
      <div style="margin-top:0.75rem;">
        <div style="margin-bottom:0.5rem;font-size:0.8125rem;color:var(--text-secondary);font-weight:600;">
          Select two evaluations to compare:
        </div>
        <div class="compare-selection">
          ${evaluations.map((ev, i) => {
            const label = i === 0 ? 'Latest' : '#' + (evaluations.length - i);
            const date = escapeHtml(new Date(ev.timestamp).toLocaleDateString());
            const scoreText = ev.complianceScore != null ? ` — ${Number(ev.complianceScore)}%` : '';
            return `
              <label style="display:flex;align-items:center;gap:0.5rem;padding:0.375rem 0;font-size:0.8125rem;cursor:pointer;">
                <input type="checkbox" name="compare-eval" value="${escapeHtml(ev.id)}"
                  data-change="compareSelectionChange" style="cursor:pointer;">
                <span>${escapeHtml(label)} (${date}${scoreText})</span>
              </label>`;
          }).join('')}
        </div>
        <button class="btn-compare" data-click="compareSelected" disabled aria-label="Compare selected evaluations">
          Compare Selected
        </button>
      </div>`);
  }

  function _onSelectionChange() {
    const checked = document.querySelectorAll('input[name="compare-eval"]:checked');
    const btn = document.querySelector('.btn-compare');
    if (!btn) return;

    // Allow exactly 2 selections
    if (checked.length > 2) {
      // Uncheck the oldest selection (first checked)
      checked[0].checked = false;
    }

    const currentChecked = document.querySelectorAll('input[name="compare-eval"]:checked');
    btn.disabled = currentChecked.length !== 2;
  }

  function _onCompareClick() {
    const checked = document.querySelectorAll('input[name="compare-eval"]:checked');
    if (checked.length !== 2) return;
    startComparison(checked[0].value, checked[1].value);
  }

  Actions.on('swapComparison', () => swapComparison());
  Actions.on('exitComparison', () => exitComparison());
  Actions.on('compareSelectionChange', () => _onSelectionChange());
  Actions.on('compareSelected', () => _onCompareClick());

  return {
    shouldShowCompareButton,
    diffViolations,
    startComparison,
    exitComparison,
    swapComparison,
    renderCompareButton,
    _onSelectionChange,
    _onCompareClick
  };
})();
