/* Compliance Checklist Module */

const Checklist = (function () {
  const CATEGORIES = [
    { id: 'drug-facts-panel', name: 'Drug Facts Panel', keywords: ['drug facts', 'panel', 'format', 'layout'] },
    { id: 'active-ingredients', name: 'Active Ingredients', keywords: ['active ingredient', 'dosage', 'strength'] },
    { id: 'warnings', name: 'Warnings', keywords: ['warning', 'caution', 'contraindication', 'allergy', 'side effect'] },
    { id: 'directions', name: 'Directions', keywords: ['direction', 'dosage', 'administration', 'usage'] },
    { id: 'uses-indications', name: 'Uses/Indications', keywords: ['use', 'indication', 'purpose', 'symptom'] },
    { id: 'inactive-ingredients', name: 'Inactive Ingredients', keywords: ['inactive ingredient', 'excipient'] },
    { id: 'other-information', name: 'Other Information', keywords: ['storage', 'tamper', 'expiration', 'lot'] }
  ];

  const CATCH_ALL = { id: 'general-labeling', name: 'General Labeling', keywords: [] };

  const SEVERITY_ORDER = { high: 0, medium: 1, low: 2 };

  let categorizedData = [];

  // Match a single violation to a category by keyword search on title + description. Returns the first matching category, or the catch-all.
  function matchCategory(violation) {
    const text = ((violation.title || '') + ' ' + (violation.description || '')).toLowerCase();
    for (const cat of CATEGORIES) {
      for (const kw of cat.keywords) {
        if (text.indexOf(kw) !== -1) {
          return cat;
        }
      }
    }
    return CATCH_ALL;
  }

  // Categorize an array of violations into regulatory groups. Each violation is assigned to exactly one category.
  function categorizeViolations(violations) {
    const map = {};

    // Initialize all categories (including catch-all) with empty arrays
    CATEGORIES.concat(CATCH_ALL).forEach(function (cat) {
      map[cat.id] = { id: cat.id, name: cat.name, violations: [] };
    });

    (violations || []).forEach(function (v) {
      if (v.severity === 'info') return; // skip info-level items
      var cat = matchCategory(v);
      map[cat.id].violations.push(v);
    });

    // Return all categories sorted alphabetically by name
    return CATEGORIES.concat(CATCH_ALL).map(function (cat) {
      return map[cat.id];
    }).sort(function (a, b) {
      return a.name.localeCompare(b.name);
    });
  }

  // Get the status summary for a single category. Returns { status: 'pass'|'fail', count, highestSeverity }
  function getCategoryStatus(category) {
    var count = category.violations.length;
    if (count === 0) {
      return { status: 'pass', count: 0, highestSeverity: null };
    }

    var highestSeverity = 'low';
    category.violations.forEach(function (v) {
      var sev = v.severity || 'low';
      if (SEVERITY_ORDER[sev] < SEVERITY_ORDER[highestSeverity]) {
        highestSeverity = sev;
      }
    });

    return { status: 'fail', count: count, highestSeverity: highestSeverity };
  }

  // Render a single violation card inside an expanded category.
  function renderViolationCard(violation) {
    var severity = escapeHtml(violation.severity || '');
    return '<div class="violation-item ' + severity + '">' +
      '<div class="violation-header">' +
        '<div class="violation-title">' + escapeHtml(violation.title || '') + '</div>' +
        '<span class="severity-badge ' + severity + '">' + severity + '</span>' +
      '</div>' +
      '<div class="violation-description">' + escapeHtml(violation.description || '') + '</div>' +
    '</div>';
  }

  // Build the status icon SVG (checkmark for pass, X for fail).
  function statusIcon(status) {
    if (status === 'pass') {
      return '<div class="checklist-status-icon pass">' +
        '<svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">' +
          '<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/>' +
        '</svg>' +
      '</div>';
    }
    return '<div class="checklist-status-icon fail">' +
      '<svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">' +
        '<path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"/>' +
      '</svg>' +
    '</div>';
  }

  // Render the full checklist accordion into the given container element.
  function render(container) {
    if (!container) return;

    categorizedData = categorizeViolations(
      (typeof currentProject !== 'undefined' && currentProject && currentProject.formattedViolations) || []
    );

    var html = '<div class="checklist-container">' +
      '<div class="checklist-header"><h3>Compliance Checklist</h3></div>';

    categorizedData.forEach(function (cat) {
      var st = getCategoryStatus(cat);
      var safeCatId = escapeHtml(cat.id);
      html += '<div class="checklist-category" data-category-id="' + safeCatId + '">';

      // Header row
      html += '<div class="checklist-category-header" onclick="Checklist.toggleCategory(\'' + safeCatId + '\')" ' +
        'role="button" tabindex="0" aria-expanded="false" ' +
        'aria-label="' + escapeHtml(cat.name) + ' — ' + escapeHtml(st.status) + '">';
      html += statusIcon(st.status);
      html += '<span class="checklist-category-name">' + escapeHtml(cat.name) + '</span>';

      if (st.status === 'fail') {
        html += '<span class="checklist-count">' + Number(st.count) + ' violation' + (st.count !== 1 ? 's' : '') + '</span>';
        html += '<span class="checklist-severity-pill ' + escapeHtml(st.highestSeverity) + '">' + escapeHtml(st.highestSeverity) + '</span>';
      }

      html += '</div>'; // end header

      // Expandable content
      html += '<div class="checklist-category-content"><div class="checklist-violations">';
      cat.violations.forEach(function (v) {
        html += renderViolationCard(v);
      });
      html += '</div></div>';

      html += '</div>'; // end category
    });

    html += '</div>'; // end container
    setSafeHTML(container, html);
  }

  // Toggle expand/collapse for a category by its ID.
  function toggleCategory(categoryId) {
    var el = document.querySelector('.checklist-category[data-category-id="' + categoryId + '"]');
    if (!el) return;

    var isExpanded = el.classList.contains('expanded');
    el.classList.toggle('expanded');

    var header = el.querySelector('.checklist-category-header');
    if (header) {
      header.setAttribute('aria-expanded', String(!isExpanded));
    }
  }

  // Public API
  return {
    categorizeViolations: categorizeViolations,
    getCategoryStatus: getCategoryStatus,
    render: render,
    toggleCategory: toggleCategory
  };
})();
