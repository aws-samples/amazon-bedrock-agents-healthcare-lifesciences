/* Settings Page Module */

const Settings = (function () {

  const REGION_META = {
    US_FDA: { flag: '🇺🇸', label: 'United States — FDA' },
    UK_MHRA: { flag: '🇬🇧', label: 'United Kingdom — MHRA' }
  };

  let pendingFile = null;
  let uploadRegion = null;

  // Profile

  function loadProfile() {
    const p = JSON.parse(localStorage.getItem('userProfile') || '{}');
    if (p.name) document.getElementById('settingsName').value = p.name;
    if (p.email) document.getElementById('settingsEmail').value = p.email;
    if (p.org) document.getElementById('settingsOrg').value = p.org;
    if (p.role) document.getElementById('settingsRole').value = p.role;
  }

  function saveProfile(e) {
    e.preventDefault();
    localStorage.setItem('userProfile', JSON.stringify({
      name: document.getElementById('settingsName').value,
      email: document.getElementById('settingsEmail').value,
      org: document.getElementById('settingsOrg').value,
      role: document.getElementById('settingsRole').value
    }));
    showToast('Profile saved');
  }

  // Tabs

  function switchTab(tabId) {
    document.querySelectorAll('.settings-tab').forEach(function (t) {
      t.classList.toggle('active', t.dataset.tab === tabId);
    });
    document.querySelectorAll('.settings-panel').forEach(function (p) {
      p.style.display = p.id === 'tab-' + tabId ? '' : 'none';
    });
    if (tabId === 'documents') fetchAndRenderDocs();
  }

  // Fetch documents from API

  async function fetchAndRenderDocs() {
    const container = document.getElementById('regulatoryDocsContainer');
    console.log('fetchAndRenderDocs called, container:', container);
    if (!container) return;
    container.innerHTML = '<div style="text-align:center;padding:2rem;color:#94a3b8;">Loading documents...</div>';
    try {
      const url = API_ENDPOINT + '/documents/list';
      console.log('Fetching:', url);
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      if (!resp.ok) throw new Error('Failed to fetch: ' + resp.status);
      const data = await resp.json();
      console.log('Documents data:', data);
      renderDocs(container, data);
    } catch (err) {
      console.error('Fetch docs error:', err);
      container.innerHTML = '<div style="text-align:center;padding:2rem;color:#dc2626;">Failed to load documents. Check your connection.</div>';
    }
  }

  function renderDocs(container, data) {
    let html = '';
    for (const regionKey in REGION_META) {
      const meta = REGION_META[regionKey];
      const regionData = data[regionKey];
      const docs = regionData ? regionData.documents || [] : [];
      html += '<div class="settings-card" style="margin-bottom:1.5rem;">';
      html += '<div class="settings-card-header">';
      html += '<div><h2>' + meta.flag + ' ' + meta.label + '</h2>';
      html += '<p>' + docs.length + ' document' + (docs.length !== 1 ? 's' : '') + ' in knowledge base</p></div>';
      html += '<button class="btn-primary btn-sm" onclick="Settings.showUploadModal(\'' + regionKey + '\')">';
      html += '<svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"/></svg>';
      html += ' Add Document</button></div>';
      if (docs.length === 0) {
        html += '<div class="doc-empty">No documents found!</div>';
      } else {
        html += '<div class="doc-list">';
        docs.forEach(function (doc) {
          var sizeKB = doc.size ? Math.round(doc.size / 1024) : 0;
          var date = doc.lastModified ? new Date(doc.lastModified).toLocaleDateString() : '';
          html += '<div class="doc-item"><div class="doc-item-info">';
          html += '<div class="doc-item-name">' + escapeHtml(doc.name) + '</div>';
          html += '<div class="doc-item-desc">' + sizeKB + ' KB · Uploaded ' + escapeHtml(date) + '</div>';
          html += '</div><div class="doc-item-meta">';
          html += '<span class="doc-status-badge active">Active</span>';
          html += '<button class="doc-action-btn" onclick="Settings.downloadDoc(\'' + regionKey + '\',\'' + escapeAttr(doc.key) + '\')" title="Download" aria-label="Download document">⬇</button>';
          html += '<button class="doc-remove-btn" onclick="Settings.deleteDoc(\'' + regionKey + '\',\'' + escapeAttr(doc.key) + '\')" title="Delete">✕</button>';
          html += '</div></div>';
        });
        html += '</div>';
      }
      html += '</div>';
    }
    setSafeHTML(container, html);
  }

  // Upload

  function showUploadModal(region) {
    uploadRegion = region;
    pendingFile = null;
    var meta = REGION_META[region] || {};
    document.getElementById('uploadRegionLabel').textContent = meta.flag + ' ' + (meta.label || region);
    document.getElementById('docUploadLabel').textContent = 'Choose a file';
    document.getElementById('docUploadBtn').disabled = true;
    document.getElementById('docUploadProgress').style.display = 'none';
    document.getElementById('docFileInput').value = '';
    document.getElementById('uploadDocModal').classList.add('active');
    var zone = document.getElementById('docUploadZone');
    var input = document.getElementById('docFileInput');
    zone.onclick = function () { input.click(); };
    input.onchange = function (e) {
      if (e.target.files.length) {
        pendingFile = e.target.files[0];
        document.getElementById('docUploadLabel').textContent = pendingFile.name;
        document.getElementById('docUploadBtn').disabled = false;
      }
    };
  }

  function closeUploadModal() {
    document.getElementById('uploadDocModal').classList.remove('active');
    pendingFile = null;
    uploadRegion = null;
  }

  async function confirmUpload() {
    if (!pendingFile || !uploadRegion) return;
    var btn = document.getElementById('docUploadBtn');
    var progress = document.getElementById('docUploadProgress');
    var status = document.getElementById('docUploadStatus');
    btn.disabled = true;
    progress.style.display = 'block';
    status.textContent = 'Getting upload URL...';
    try {
      var urlResp = await fetch(API_ENDPOINT + '/documents/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ region: uploadRegion, filename: pendingFile.name, contentType: pendingFile.type || 'application/pdf' })
      });
      if (!urlResp.ok) { var err = await urlResp.json(); throw new Error(err.error || 'Upload failed'); }
      var urlData = await urlResp.json();
      status.textContent = 'Uploading file...';
      var s3Resp = await fetch(urlData.uploadUrl, {
        method: 'PUT',
        headers: { 'Content-Type': pendingFile.type || 'application/pdf' },
        body: pendingFile
      });
      if (!s3Resp.ok) throw new Error('S3 upload failed');
      status.textContent = 'Syncing knowledge base...';
      await fetch(API_ENDPOINT + '/documents/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ region: uploadRegion })
      });
      closeUploadModal();
      showToast('Document uploaded and sync started');
      fetchAndRenderDocs();
    } catch (err) {
      console.error('Upload error:', err);
      status.textContent = 'Error: ' + err.message;
      btn.disabled = false;
    }
  }

  // Download

  async function downloadDoc(region, key) {
    try {
      var resp = await fetch(API_ENDPOINT + '/documents/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ region: region, key: key })
      });
      if (!resp.ok) { var err = await resp.json(); throw new Error(err.error || 'Download failed'); }
      var data = await resp.json();
      window.open(data.downloadUrl, '_blank');
    } catch (err) {
      console.error('Download error:', err);
      alert('Failed to download: ' + err.message);
    }
  }

  // Delete

  async function deleteDoc(region, key) {
    if (!confirm('Delete this document? It will be removed from the knowledge base.')) return;
    try {
      var resp = await fetch(API_ENDPOINT + '/documents/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ region: region, key: key })
      });
      if (!resp.ok) { var err = await resp.json(); throw new Error(err.error || 'Delete failed'); }
      await fetch(API_ENDPOINT + '/documents/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ region: region })
      });
      showToast('Document deleted and sync started');
      fetchAndRenderDocs();
    } catch (err) {
      console.error('Delete error:', err);
      alert('Failed to delete: ' + err.message);
    }
  }

  // Utilities

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // Safely render a trusted-but-dynamic HTML string into an element without using the
  // `.innerHTML` setter. The markup is parsed in an inert document (scripts are not run)
  // and the resulting nodes replace the element's children. All dynamic values embedded
  // in the markup are still escaped via escapeHtml()/escapeAttr() at the call sites.
  function setSafeHTML(element, htmlString) {
    if (!element) return;
    var parsed = new DOMParser().parseFromString(String(htmlString), 'text/html');
    element.replaceChildren.apply(element, Array.prototype.slice.call(parsed.body.childNodes));
  }

  function escapeAttr(str) {
    return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
  }

  function showToast(message) {
    var existing = document.querySelector('.settings-toast');
    if (existing) existing.remove();
    var toast = document.createElement('div');
    toast.className = 'settings-toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(function () { toast.classList.add('visible'); }, 10);
    setTimeout(function () {
      toast.classList.remove('visible');
      setTimeout(function () { toast.remove(); }, 300);
    }, 2000);
  }

  // Init 
  document.addEventListener('DOMContentLoaded', async function () {
    if (window.__authReady && !(await window.__authReady)) return;
    loadProfile();
    var openTab = localStorage.getItem('settingsOpenTab');
    if (openTab) {
      localStorage.removeItem('settingsOpenTab');
      switchTab(openTab);
    }
  });

  return {
    switchTab: switchTab,
    saveProfile: saveProfile,
    showUploadModal: showUploadModal,
    closeUploadModal: closeUploadModal,
    confirmUpload: confirmUpload,
    downloadDoc: downloadDoc,
    deleteDoc: deleteDoc
  };
})();
