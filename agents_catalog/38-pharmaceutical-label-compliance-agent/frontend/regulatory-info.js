/* Regulatory Info Panel Module */

const RegulatoryInfo = (function () {
  // Static regulatory data
  const REGULATORY_DATA = {
    US_FDA: {
      regionCode: 'US_FDA',
      title: 'FDA 21 CFR Part 201',
      flag: '\u{1F1FA}\u{1F1F8}',
      subtitle: 'OTC Drug Labeling Requirements'
    },
    UK_MHRA: {
      regionCode: 'UK_MHRA',
      title: 'Human Medicines Regulations 2012',
      flag: '\u{1F1EC}\u{1F1E7}',
      subtitle: 'MHRA Labeling Requirements'
    }
  };

  let currentData = null;

  function init(region) {
    currentData = REGULATORY_DATA[region] || null;
  }

  function render(container) {
    if (!currentData || !container) return;

    container.textContent = '';

    const panel = document.createElement('div');
    panel.className = 'regulatory-panel';
    panel.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:1rem 1.25rem;';

    const infoGroup = document.createElement('div');
    infoGroup.style.cssText = 'display:flex;align-items:center;gap:0.75rem;';

    const flag = document.createElement('span');
    flag.style.fontSize = '1.25rem';
    flag.textContent = currentData.flag;

    const textGroup = document.createElement('div');

    const title = document.createElement('div');
    title.style.cssText = 'font-weight:700;font-size:0.9375rem;color:var(--text);';
    title.textContent = currentData.title;

    const subtitle = document.createElement('div');
    subtitle.style.cssText = 'font-size:0.8125rem;color:var(--text-muted);';
    subtitle.textContent = currentData.subtitle;

    textGroup.appendChild(title);
    textGroup.appendChild(subtitle);
    infoGroup.appendChild(flag);
    infoGroup.appendChild(textGroup);

    const link = document.createElement('a');
    link.href = 'settings.html';
    link.style.cssText = 'font-size:0.8125rem;font-weight:600;color:var(--primary);text-decoration:none;display:flex;align-items:center;gap:0.375rem;';
    link.textContent = 'View Documents ';
    link.addEventListener('click', function () {
      localStorage.setItem('settingsOpenTab', 'documents');
    });

    const arrow = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    arrow.setAttribute('width', '14');
    arrow.setAttribute('height', '14');
    arrow.setAttribute('viewBox', '0 0 20 20');
    arrow.setAttribute('fill', 'currentColor');
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('fill-rule', 'evenodd');
    path.setAttribute('d', 'M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z');
    arrow.appendChild(path);
    link.appendChild(arrow);

    panel.appendChild(infoGroup);
    panel.appendChild(link);
    container.appendChild(panel);
  }

  return { init: init, render: render };
})();
