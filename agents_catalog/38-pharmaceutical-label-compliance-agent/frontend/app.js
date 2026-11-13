function updateStats() {
  const projects = ProjectDB.getCachedProjects();
  document.getElementById('totalProjects').textContent = projects.length;
  document.getElementById('completedProjects').textContent = projects.filter(p => p.status === 'complete').length;
  document.getElementById('processingProjects').textContent = projects.filter(p => p.status === 'processing').length;
}

function renderProjects() {
  const projects = ProjectDB.getCachedProjects();
  const grid = document.getElementById('projectsGrid');
  
  if (projects.length === 0) {
    grid.innerHTML = `
      <div class="empty-state">
        <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
        </svg>
        <h3>No projects yet</h3>
        <p>Create your first compliance analysis project to get started</p>
      </div>
    `;
    return;
  }
  
  const sorted = [...projects].sort((a, b) => b.timestamp - a.timestamp);
  
  setSafeHTML(grid, sorted.map(project => {
    const safeId = escapeHtml(project.id);
    const safeName = escapeHtml(project.name);
    const safeDesc = project.description ? escapeHtml(project.description) : '';
    const safeRegion = escapeHtml(project.region.replace('_', ' '));
    const safeStatus = escapeHtml(project.status);
    const score = Number(project.complianceScore);
    const evalCount = project.evaluations ? Number(project.evaluations.length) : 0;
    return `
    <div class="project-card" onclick="openProject('${safeId}')">
      <button class="project-delete" onclick="deleteProject(event, '${safeId}')" aria-label="Delete project">
        <svg width="18" height="18" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"/>
        </svg>
      </button>
      <div class="project-header">
        <div class="project-name">${safeName}</div>
        ${safeDesc ? `<div class="project-desc">${safeDesc}</div>` : ''}
      </div>
      ${project.complianceScore !== undefined ? `
        <div class="compliance-score">
          <div class="score-label">Compliance Score</div>
          <div class="score-value ${getScoreClass(score)}">${score}% <span class="score-status">(${getScoreLabel(score)})</span></div>
        </div>
      ` : ''}
      <div class="project-meta">
        <span>${safeRegion}</span>
        <span>•</span>
        <span>${escapeHtml(new Date(project.timestamp).toLocaleDateString())}</span>
        ${evalCount > 0 ? `
          <span>•</span>
          <span>${evalCount} evaluation${evalCount > 1 ? 's' : ''}</span>
        ` : ''}
      </div>
      <div class="project-status ${safeStatus}">
        ${project.status === 'processing' ? '⏳' : project.status === 'complete' ? '✓' : '○'}
        ${safeStatus.charAt(0).toUpperCase() + safeStatus.slice(1)}
      </div>
    </div>
  `;}).join(''));
}

function getScoreClass(score) {
  if (score >= 90) return 'excellent';
  if (score >= 70) return 'good';
  if (score >= 50) return 'fair';
  return 'poor';
}

// Text label so compliance status is conveyed without relying on color alone.
function getScoreLabel(score) {
  if (score >= 90) return 'Excellent';
  if (score >= 70) return 'Good';
  if (score >= 50) return 'Fair';
  return 'Poor';
}

function openCreateModal() {
  document.getElementById('createModal').classList.add('active');
}

function closeCreateModal() {
  const modal = document.getElementById('createModal');
  modal.classList.remove('active');
  document.getElementById('projectName').value = '';
  document.getElementById('projectDescription').value = '';
}

async function createProject(event) {
  event.preventDefault();
  
  const project = {
    id: crypto.randomUUID(),
    name: document.getElementById('projectName').value,
    region: document.getElementById('projectRegion').value,
    description: document.getElementById('projectDescription').value,
    status: 'idle',
    timestamp: Date.now(),
    evaluations: []
  };

  await ProjectDB.saveProject(project);
  window.location.href = `project.html?id=${project.id}`;
}

function openProject(id) {
  window.location.href = `project.html?id=${id}`;
}

async function deleteProject(event, id) {
  event.stopPropagation();
  if (!confirm('Delete this project? This action cannot be undone.')) return;
  
  await ProjectDB.deleteProject(id);
  updateStats();
  renderProjects();
  renderAnalytics();
}

// === Analytics Functions ===

function calculateAverageScore(projects) {
  const completed = projects.filter(
    p => p.status === 'complete' && p.complianceScore !== undefined && p.complianceScore !== null
  );
  if (completed.length === 0) return null;
  const sum = completed.reduce((acc, p) => acc + p.complianceScore, 0);
  return Math.round(sum / completed.length);
}

function calculateDistribution(projects) {
  const completed = projects.filter(
    p => p.status === 'complete' && p.complianceScore !== undefined && p.complianceScore !== null
  );
  const total = completed.length;
  const buckets = [
    { label: '0-49', displayName: 'Critical', min: 0, max: 49, color: '#dc2626', count: 0 },
    { label: '50-69', displayName: 'Needs Work', min: 50, max: 69, color: '#d97706', count: 0 },
    { label: '70-89', displayName: 'Good', min: 70, max: 89, color: '#2563eb', count: 0 },
    { label: '90-100', displayName: 'Excellent', min: 90, max: 100, color: '#059669', count: 0 }
  ];
  completed.forEach(p => {
    for (const bucket of buckets) {
      if (p.complianceScore >= bucket.min && p.complianceScore <= bucket.max) {
        bucket.count++;
        break;
      }
    }
  });
  return buckets.map(b => ({
    label: b.label, displayName: b.displayName, count: b.count,
    percentage: total > 0 ? Math.round((b.count / total) * 100) : 0, color: b.color
  }));
}

function renderAnalytics() {
  const container = document.getElementById('analyticsSection');
  if (!container) return;
  const projects = ProjectDB.getCachedProjects();
  const avg = calculateAverageScore(projects);
  const distribution = calculateDistribution(projects);
  if (avg === null) { container.innerHTML = ''; return; }

  const scoreColorMap = { excellent: '#059669', good: '#2563eb', fair: '#d97706', poor: '#dc2626' };
  const scoreClass = getScoreClass(avg);
  const scoreColor = scoreColorMap[scoreClass] || '#0d9488';

  const avgCard = `
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
      <div style="padding:1rem 1.25rem;border-bottom:1px solid #e2e8f0;font-size:0.875rem;font-weight:700;color:#1e293b;">Average Compliance</div>
      <div style="padding:1.25rem;">
        <div style="display:flex;flex-direction:column;align-items:center;padding:1rem 0;">
          <div style="font-size:2.5rem;font-weight:800;line-height:1;color:${scoreColor};">${avg}%</div>
          <div style="font-size:0.8125rem;color:#94a3b8;margin-top:0.5rem;">across completed projects</div>
        </div>
      </div>
    </div>`;

  const segments = distribution.filter(d => d.percentage > 0).map(d =>
    `<div style="width:${d.percentage}%;background:${d.color};display:flex;align-items:center;justify-content:center;font-size:0.6875rem;font-weight:700;color:#fff;" title="${d.displayName}: ${d.count} project${d.count !== 1 ? 's' : ''} (${d.percentage}%)">${d.percentage}%</div>`
  ).join('');

  const legendItems = distribution.map(d =>
    `<div style="display:flex;align-items:center;gap:0.5rem;font-size:0.8125rem;">
      <span style="background:${d.color};width:10px;height:10px;border-radius:2px;display:inline-block;flex-shrink:0;"></span>
      <span style="color:#1e293b;font-weight:600;">${d.displayName}:</span>
      <span style="color:#1e293b;font-weight:700;">${d.count}</span>
    </div>`
  ).join('');

  const distCard = `
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
      <div style="padding:1rem 1.25rem;border-bottom:1px solid #e2e8f0;font-size:0.875rem;font-weight:700;color:#1e293b;">Score Distribution</div>
      <div style="padding:1.25rem;">
        <div style="display:flex;height:32px;border-radius:8px;overflow:hidden;background:#f8fafc;border:1px solid #e2e8f0;">${segments}</div>
        <div style="display:flex;flex-wrap:wrap;gap:0.75rem;margin-top:1rem;">${legendItems}</div>
      </div>
    </div>`;

  setSafeHTML(container, avgCard + distCard);
}

document.addEventListener('DOMContentLoaded', async () => {
  if (window.__authReady && !(await window.__authReady)) return;
  // Show loading state
  const grid = document.getElementById('projectsGrid');
  grid.innerHTML = '<div class="empty-state"><p>Loading projects...</p></div>';
  
  try {
    await ProjectDB.fetchProjects();
  } catch (e) {
    console.error('Failed to load projects:', e);
    grid.innerHTML = '<div class="empty-state"><p>Failed to load projects. Please refresh.</p></div>';
    return;
  }
  
  updateStats();
  renderProjects();
  renderAnalytics();
  
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      const query = e.target.value.toLowerCase();
      const cards = document.querySelectorAll('.project-card');
      cards.forEach(card => {
        const text = card.textContent.toLowerCase();
        card.style.display = text.includes(query) ? '' : 'none';
      });
    });
  }
});
