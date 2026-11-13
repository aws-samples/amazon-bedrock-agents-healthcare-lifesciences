/*
 * actions.js — event delegation for elements marked with data-click,
 * data-change, or data-submit.
 *
 * The site's Content-Security-Policy (script-src 'self') blocks inline event
 * handlers such as onclick="...". Instead, markup names an action and page
 * scripts register a handler for it:
 *
 *   <button data-click="openProject" data-id="123">Open</button>
 *   Actions.on('openProject', (event, el) => openProject(el.dataset.id));
 *
 * Handlers receive the DOM event and the element that carries the attribute.
 * Load this file before any page script that calls Actions.on.
 */
const Actions = (function () {
  'use strict';

  const handlers = {};

  function on(name, handler) {
    handlers[name] = handler;
  }

  ['click', 'change', 'submit'].forEach(function (eventType) {
    const attr = 'data-' + eventType;
    document.addEventListener(eventType, function (event) {
      const el = event.target instanceof Element ? event.target.closest('[' + attr + ']') : null;
      if (!el) return;
      const handler = handlers[el.getAttribute(attr)];
      if (handler) handler(event, el);
    });
  });

  return { on: on };
})();
