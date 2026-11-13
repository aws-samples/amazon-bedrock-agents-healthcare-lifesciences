const urlParams = new URLSearchParams(window.location.search);
const projectId = urlParams.get('id');
let currentProject = null;
let pollingInterval = null;
let pendingFile = null;

function updateProject(updates) {
  if (!currentProject) return;
  Object.assign(currentProject, updates);
  // Update cache and debounce the API write
  ProjectDB.saveProjectDebounced(currentProject);
}

async function updateProjectImmediate(updates) {
  if (!currentProject) return;
  Object.assign(currentProject, updates);
  await ProjectDB.saveProject(currentProject);
}

async function loadProject() {
  try {
    await ProjectDB.fetchProjects();
  } catch (e) {
    console.error('Failed to load projects:', e);
    window.location.href = 'index.html';
    return;
  }

  currentProject = ProjectDB.getCachedProjects().find(p => p.id === projectId);
  
  if (!currentProject) {
    window.location.href = 'index.html';
    return;
  }
  
  if (!currentProject.evaluations) {
    // Initialize in memory only. Do NOT persist an empty array here: if this
    // load ever races with a write, saving [] would wipe existing evaluations.
    currentProject.evaluations = [];
  }
  
  document.getElementById('projectTitle').textContent = currentProject.name;
  document.getElementById('projectRegion').textContent = currentProject.region.replace('_', ' - ');
  
  if (typeof RegulatoryInfo !== 'undefined') {
    RegulatoryInfo.init(currentProject.region);
    RegulatoryInfo.render(document.getElementById('regulatoryInfoPanel'));
  }
  
  if (currentProject.status === 'processing') {
    showProcessing();
    startPolling();
  } else if (currentProject.status === 'complete') {
    showResults();
  }
}

function showReupload() {
  document.getElementById('uploadTitle').textContent = 'Re-upload Medicine Label';
  document.getElementById('uploadSection').style.display = 'block';
  document.getElementById('confirmationSection').classList.remove('active');
  document.getElementById('resultsSection').classList.remove('active');
}

function setupUpload() {
  const zone = document.getElementById('uploadZone');
  const input = document.getElementById('fileInput');
  
  zone.onclick = () => input.click();
  
  zone.ondragover = (e) => {
    e.preventDefault();
    zone.classList.add('dragover');
  };
  
  zone.ondragleave = () => zone.classList.remove('dragover');
  
  zone.ondrop = (e) => {
    e.preventDefault();
    zone.classList.remove('dragover');
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
  };
  
  input.onchange = (e) => {
    if (e.target.files.length) handleFile(e.target.files[0]);
  };
}

async function handleFile(file) {
  if (!file.type.startsWith('image/')) {
    alert('Please upload an image file (JPG or PNG)');
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    alert('File size must be less than 10MB');
    return;
  }
  
  pendingFile = file;
  
  const reader = new FileReader();
  reader.onload = (e) => {
    const img = document.getElementById('previewImage');
    img.src = e.target.result;
    const tempImg = new Image();
    tempImg.onload = () => {
      document.getElementById('fileDimensions').textContent = `${tempImg.width} × ${tempImg.height}px`;
    };
    tempImg.src = e.target.result;
  };
  reader.readAsDataURL(file);
  
  document.getElementById('fileName').textContent = file.name;
  document.getElementById('fileSize').textContent = formatFileSize(file.size);
  
  document.getElementById('uploadSection').style.display = 'none';
  document.getElementById('confirmationSection').classList.add('active');
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function cancelAnalysis() {
  pendingFile = null;
  document.getElementById('confirmationSection').classList.remove('active');
  document.getElementById('uploadSection').style.display = 'block';
  document.getElementById('uploadTitle').textContent = 'Upload Medicine Label';
}

async function confirmAnalysis() {
  if (!pendingFile) return;
  
  try {
    const confirmBtn = document.querySelector('.btn-confirm');
    confirmBtn.disabled = true;
    confirmBtn.textContent = 'Uploading...';
    
    const uploadResponse = await fetch(`${API_ENDPOINT}/upload`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: pendingFile.name,
        contentType: pendingFile.type,
        region: currentProject.region,
        projectId: currentProject.id
      })
    });
    
    if (!uploadResponse.ok) throw new Error(`Upload failed: ${uploadResponse.status}`);
    const uploadData = await uploadResponse.json();
    
    const s3Response = await fetch(uploadData.uploadUrl, {
      method: 'PUT',
      headers: { 'Content-Type': pendingFile.type },
      body: pendingFile
    });
    
    if (!s3Response.ok) throw new Error(`S3 upload failed: ${s3Response.status}`);
    
    // Immediate save (reset progress so polls don't pick up stale values from previous run)
    await updateProjectImmediate({
      status: 'processing',
      imageKey: uploadData.key,
      uploadTime: Date.now(),
      progress: { step1: false, step2: false, step3: false }
    });
    
    pendingFile = null;
    
    showProcessing();
    startPolling();
    
  } catch (error) {
    console.error('Upload error:', error);
    alert('Upload failed: ' + error.message);
    const confirmBtn = document.querySelector('.btn-confirm');
    confirmBtn.disabled = false;
    confirmBtn.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/>
      </svg>
      Start Analysis
    `;
  }
}

function showProcessing() {
  document.getElementById('uploadSection').style.display = 'none';
  document.getElementById('confirmationSection').classList.remove('active');
  document.getElementById('processingSection').classList.add('active');
  document.getElementById('resultsSection').classList.remove('active');
  
  // Reset all steps to initial state (important for re-uploads)
  ['step1', 'step2', 'step3', 'step4'].forEach(id => {
    const el = document.getElementById(id);
    el.classList.remove('active', 'complete');
  });
  
  document.getElementById('step1').classList.add('active');
}

function showResults() {
  document.getElementById('uploadSection').style.display = 'none';
  document.getElementById('processingSection').classList.remove('active');
  document.getElementById('resultsSection').classList.add('active');
  loadResults();
}

function startPolling() {
  pollingInterval = setInterval(checkStatus, 3000);
  checkStatus();
}

async function checkStatus() {
  try {
    const response = await fetch(`${API_ENDPOINT}/check`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        key: currentProject.imageKey,
        uploadTimestamp: currentProject.uploadTime,
        projectId: currentProject.id
      })
    });
    
    if (!response.ok) return;
    const data = await response.json();
    
    if (data.progress) {
      if (data.progress.step1) {
        document.getElementById('step1').classList.remove('active');
        document.getElementById('step1').classList.add('complete');
        if (!document.getElementById('step2').classList.contains('complete')) {
          document.getElementById('step2').classList.add('active');
        }
      }
      if (data.progress.step2) {
        document.getElementById('step2').classList.remove('active');
        document.getElementById('step2').classList.add('complete');
        if (!document.getElementById('step3').classList.contains('complete')) {
          document.getElementById('step3').classList.add('active');
        }
      }
      if (data.progress.step3) {
        document.getElementById('step3').classList.remove('active');
        document.getElementById('step3').classList.add('complete');
        if (!document.getElementById('step4').classList.contains('complete')) {
          document.getElementById('step4').classList.add('active');
        }
      }
    }
    
    if (data.status === 'completed') {
      clearInterval(pollingInterval);
      
      document.getElementById('step4').classList.add('active');
      setTimeout(() => {
        document.getElementById('step4').classList.remove('active');
        document.getElementById('step4').classList.add('complete');
      }, 500);
      
      // Re-fetch the authoritative record (strongly consistent) so the new evaluation and full history are picked up, then show results.
      try {
        await ProjectDB.fetchProjects();
        const freshProject = ProjectDB.getCachedProjects().find(p => p.id === projectId);
        if (freshProject) {
          currentProject = freshProject;
        }
      } catch (e) {
        console.warn('Could not refresh project after completion:', e);
      }

      setTimeout(() => showResults(), 1000);
    }
  } catch (error) {
    console.error('Polling error:', error);
  }
}

// Annotated images are private: the API returns short-lived presigned URLs for
// the project's latest image and for each evaluation. Show the image of the
// evaluation being viewed.
function currentImageUrl() {
  const evaluations = currentProject.evaluations || [];
  const current = evaluations.find(e => e.id === currentProject.currentEvaluationId);
  return (current && current.annotatedImageUrl) || currentProject.annotatedImageUrl || '';
}

async function loadResults() {
  document.getElementById('annotatedImage').src = currentImageUrl();
  
  renderEvaluationHistory();
  
  const annotatedImg = document.getElementById('annotatedImage');
  if (annotatedImg && currentProject.complianceScore !== undefined) {
    const vCount = (currentProject.formattedViolations || []).filter(v => v.severity !== 'info').length;
    annotatedImg.alt = `Annotated compliance label — Score: ${currentProject.complianceScore}%, ${vCount} violation${vCount !== 1 ? 's' : ''}`;
  }
  
  displayViolations(currentProject.formattedViolations || []);
}

function renderEvaluationHistory() {
  const container = document.getElementById('evaluationHistory');
  const evaluations = currentProject.evaluations || [];
  
  if (evaluations.length <= 1) {
    container.style.display = 'none';
    return;
  }
  
  container.style.display = 'block';
  setSafeHTML(container, `
    <div class="history-header">
      <h3>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        Evaluation History
      </h3>
      <span class="history-count">${Number(evaluations.length)} evaluations</span>
    </div>
    <div class="history-list">
      ${evaluations.map((ev, index) => `
        <div class="history-item ${ev.id === currentProject.currentEvaluationId ? 'active' : ''}"
             onclick="loadEvaluation('${escapeHtml(ev.id)}')">
          <div class="history-marker">${index === 0 ? 'Latest' : `#${Number(evaluations.length - index)}`}</div>
          <div class="history-info">
            <div class="history-date">${escapeHtml(new Date(ev.timestamp).toLocaleString())}</div>
            ${ev.complianceScore !== undefined ? `
              <div class="history-score">Score: ${Number(ev.complianceScore)}%</div>
            ` : ''}
          </div>
          ${ev.id === currentProject.currentEvaluationId ? `
            <div class="history-badge">Current</div>
          ` : ''}
        </div>
      `).join('')}
    </div>
  `);
  
  if (typeof Comparison !== 'undefined' && Comparison.shouldShowCompareButton(currentProject)) {
    const compareContainer = document.createElement('div');
    compareContainer.id = 'compareContainer';
    container.appendChild(compareContainer);
    Comparison.renderCompareButton(compareContainer);
  }
}

function loadEvaluation(evalId) {
  const evaluation = currentProject.evaluations.find(e => e.id === evalId);
  if (!evaluation) return;
  
  updateProject({
    complianceReport: evaluation.complianceReport,
    formattedViolations: evaluation.formattedViolations,
    complianceScore: evaluation.complianceScore,
    currentEvaluationId: evalId
  });
  
  loadResults();
}

function displayViolations(violations) {
  const listContainer = document.getElementById('violationsList');
  
  if (!violations || violations.length === 0) {
    listContainer.innerHTML = '<p style="text-align: center; padding: 2rem; color: var(--text-secondary);">No violations found</p>';
    document.getElementById('criticalCount').textContent = '0';
    document.getElementById('mediumCount').textContent = '0';
    document.getElementById('lowCount').textContent = '0';
    updateComplianceScore(100);
    if (typeof Checklist !== 'undefined') {
      Checklist.render(document.getElementById('complianceChecklist'));
    }
    return;
  }
  
  const filtered = violations.filter(v => v.severity !== 'info');
  
  if (filtered.length === 0) {
    listContainer.innerHTML = '<p style="text-align: center; padding: 2rem; color: var(--text-secondary);">No violations found - Label is compliant</p>';
    document.getElementById('criticalCount').textContent = '0';
    document.getElementById('mediumCount').textContent = '0';
    document.getElementById('lowCount').textContent = '0';
    updateComplianceScore(100);
    if (typeof Checklist !== 'undefined') {
      Checklist.render(document.getElementById('complianceChecklist'));
    }
    return;
  }
  
  const severityOrder = { high: 0, medium: 1, low: 2 };
  const sorted = filtered.sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);
  
  const summary = {
    high: sorted.filter(v => v.severity === 'high').length,
    medium: sorted.filter(v => v.severity === 'medium').length,
    low: sorted.filter(v => v.severity === 'low').length
  };
  
  document.getElementById('criticalCount').textContent = summary.high;
  document.getElementById('mediumCount').textContent = summary.medium;
  document.getElementById('lowCount').textContent = summary.low;
  
  const score = Math.max(0, 100 - (summary.high * 20 + summary.medium * 10 + summary.low * 5));
  updateComplianceScore(score);
  
  setSafeHTML(listContainer, sorted.map(v => `
    <div class="violation-item ${escapeHtml(v.severity)}">
      <div class="violation-header">
        <div class="violation-title">${escapeHtml(v.title)}</div>
        <span class="severity-badge ${escapeHtml(v.severity)}">${escapeHtml(v.severity)}</span>
      </div>
      <div class="violation-description">${escapeHtml(v.description)}</div>
    </div>
  `).join(''));
  
  if (typeof Checklist !== 'undefined') {
    Checklist.render(document.getElementById('complianceChecklist'));
  }
}

function updateComplianceScore(score) {
  const banner = document.getElementById('complianceBanner');
  const bannerScore = document.getElementById('bannerScore');
  
  if (banner && bannerScore) {
    bannerScore.textContent = `${score}%`;
    banner.className = 'compliance-banner';
    if (score >= 90) banner.classList.add('excellent');
    else if (score >= 70) banner.classList.add('good');
    else if (score >= 50) banner.classList.add('fair');
    else banner.classList.add('poor');
  }
  
  // Only persist the top-level score for the current view. Never write the evaluations array from the client.
  if (currentProject.currentEvaluationId) {
    const evaluations = currentProject.evaluations || [];
    const evalIndex = evaluations.findIndex(e => e.id === currentProject.currentEvaluationId);
    if (evalIndex !== -1) evaluations[evalIndex].complianceScore = score;
  }
  updateProject({ complianceScore: score });
}

function downloadImage() {
  const link = document.createElement('a');
  link.href = currentImageUrl();
  link.download = `${currentProject.name.replace(/\s+/g, '_')}_annotated.png`;
  link.click();
}

function toggleFullscreen() {
  const img = document.getElementById('annotatedImage');
  if (img.requestFullscreen) img.requestFullscreen();
  else if (img.webkitRequestFullscreen) img.webkitRequestFullscreen();
}

document.addEventListener('DOMContentLoaded', async () => {
  if (window.__authReady && !(await window.__authReady)) return;
  loadProject();
  setupUpload();
});
