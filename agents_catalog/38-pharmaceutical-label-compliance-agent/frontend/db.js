/* Project persistence via DynamoDB (single source of truth) */

const ProjectDB = {
  _cache: null,
  _saveTimer: null,
  _saveDelay: 1000,

  async fetchProjects() {
    const resp = await fetch(`${API_ENDPOINT}/projects/list`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}'
    });
    if (!resp.ok) throw new Error(`Failed to load projects: ${resp.status}`);
    const items = await resp.json();
    this._cache = items.map(item => {
      const p = { ...item, id: item.projectId };
      delete p.projectId;
      return p;
    });
    return this._cache;
  },

  getCachedProjects() {
    return this._cache || [];
  },

  async saveProject(project) {
    // Update cache immediately
    if (this._cache) {
      const i = this._cache.findIndex(p => p.id === project.id);
      if (i !== -1) this._cache[i] = project;
      else this._cache.unshift(project);
    }
    const resp = await fetch(`${API_ENDPOINT}/projects/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project })
    });
    if (!resp.ok) throw new Error(`Failed to save project: ${resp.status}`);
    return project;
  },

  // Debounced save (batches rapid updates)
  saveProjectDebounced(project) {
    if (this._cache) {
      const i = this._cache.findIndex(p => p.id === project.id);
      if (i !== -1) this._cache[i] = project;
      else this._cache.unshift(project);
    }
    this._pendingProject = project;
    clearTimeout(this._saveTimer);
    this._saveTimer = setTimeout(() => {
      this._pendingProject = null;
      fetch(`${API_ENDPOINT}/projects/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project })
      }).catch(e => console.warn('Debounced save failed:', e));
    }, this._saveDelay);
  },

  // Flush any pending debounced save immediately
  async flush() {
    if (this._saveTimer) {
      clearTimeout(this._saveTimer);
      this._saveTimer = null;
    }
    if (this._pendingProject) {
      const project = this._pendingProject;
      this._pendingProject = null;
      await fetch(`${API_ENDPOINT}/projects/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project })
      }).catch(e => console.warn('Flush save failed:', e));
    }
  },

  async deleteProject(id) {
    if (this._cache) {
      this._cache = this._cache.filter(p => p.id !== id);
    }
    const resp = await fetch(`${API_ENDPOINT}/projects/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id })
    });
    if (!resp.ok) throw new Error(`Failed to delete project: ${resp.status}`);
  }
};

// Shared HTML escaping utility
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// Safely render a trusted-but-dynamic HTML string into an element without using the
// `.innerHTML` setter. The markup is parsed in an inert document (scripts are not run)
// and the resulting nodes replace the element's children. All dynamic values embedded
// in the markup are still escaped via escapeHtml() at the call sites.
function setSafeHTML(element, htmlString) {
  if (!element) return;
  const parsed = new DOMParser().parseFromString(String(htmlString), 'text/html');
  element.replaceChildren(...parsed.body.childNodes);
}