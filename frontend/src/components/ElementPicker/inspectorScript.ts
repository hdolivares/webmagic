/**
 * Inspector Script — injected verbatim into the customer's site iframe.
 *
 * Behaviour (v2 — multi-select):
 *   • Hover → CSS outline highlight + tag tooltip
 *   • Click  → capture element metadata, postMessage to parent, show "Pinned!" flash
 *   • Does NOT close after a click — stays open for more selections
 *   • Receives WEBMAGIC_PIN_COUNT from parent to update the counter badge
 *   • Receives WEBMAGIC_SELECTION_LIMIT to disable further clicks
 *   • Esc key → cancel (posts WEBMAGIC_INSPECTOR_CANCELLED)
 */

const UTILITY_CLASS_PATTERN =
  /^(flex|grid|block|inline|hidden|absolute|relative|fixed|sticky|overflow|container|wrapper|row|col(?:umn)?-?\d*|d-|is-|js-|text-(?:xs|sm|base|lg|xl|2xl|3xl|4xl|5xl|6xl|7xl|8xl|9xl|left|right|center|justify)|bg-|p-|px-|py-|pt-|pb-|pl-|pr-|m-|mx-|my-|mt-|mb-|ml-|mr-|w-|h-|min-[wh]-|max-[wh]-|border(?:-\w+)?|rounded(?:-\w+)?|shadow(?:-\w+)?|font-(?:thin|light|normal|medium|semibold|bold|extrabold|black|\d{3})|leading-|tracking-|items-|justify-|gap-|space-[xy]-|z-\d|opacity-|cursor-|select-|sr-only|not-sr-only|\d+)/

const STYLE_KEYS = [
  'font-size',
  'font-weight',
  'font-family',
  'color',
  'background-color',
  'padding',
  'margin',
  'display',
  'text-align',
  'border-radius',
] as const

export function buildInspectorScript(): string {
  const utilityPattern = UTILITY_CLASS_PATTERN.source
  const styleKeys = JSON.stringify(STYLE_KEYS)

  return /* javascript */ `
(function () {
  'use strict';

  // ── Config ────────────────────────────────────────────────────────────────
  var UTILITY_RE = new RegExp(${JSON.stringify(utilityPattern)});
  var STYLE_KEYS  = ${styleKeys};
  var pinCount = 0;
  var pinMax   = 3;
  var limitReached = false;

  // ── Helpers ───────────────────────────────────────────────────────────────
  function semanticClasses(el) {
    return Array.from(el.classList)
      .filter(function(c) { return c.length > 2 && !UTILITY_RE.test(c); })
      .sort(function(a, b) { return b.length - a.length; })
      .slice(0, 2);
  }

  function buildSelector(el) {
    var segs = [], node = el;
    for (var d = 0; d < 6 && node && node.tagName; d++) {
      if (node.id) { segs.unshift('#' + node.id); break; }
      var tag = node.tagName.toLowerCase();
      var cls = semanticClasses(node);
      var seg = tag + (cls.length ? '.' + cls.join('.') : '');
      if (!cls.length && node.parentElement) {
        var sibs = Array.from(node.parentElement.children)
          .filter(function(s) { return s.tagName === node.tagName; });
        if (sibs.length > 1) {
          var all = Array.from(node.parentElement.children);
          seg += ':nth-child(' + (all.indexOf(node) + 1) + ')';
        }
      }
      segs.unshift(seg);
      node = node.parentElement;
    }
    return segs.join(' > ');
  }

  function buildDomPath(el) {
    var crumbs = [], node = el;
    for (var d = 0; d < 5 && node && node.tagName; d++) {
      var tag = node.tagName.toLowerCase();
      var cls = Array.from(node.classList).filter(function(c) { return !UTILITY_RE.test(c); })[0];
      crumbs.unshift(node.id ? tag + '#' + node.id : cls ? tag + '.' + cls : tag);
      node = node.parentElement;
    }
    return crumbs.join(' > ');
  }

  function getStyles(el) {
    var cs = window.getComputedStyle(el), r = {};
    STYLE_KEYS.forEach(function(k) { r[k] = cs.getPropertyValue(k).trim(); });
    return r;
  }

  // ── UI Elements ───────────────────────────────────────────────────────────

  // Hover outline overlay
  var overlay = document.createElement('div');
  overlay.id = '__wm_overlay__';
  overlay.style.cssText = 'position:fixed;pointer-events:none;z-index:2147483640;box-sizing:border-box;border:2px solid #6366f1;background:rgba(99,102,241,0.08);border-radius:3px;transition:all 70ms ease;display:none';
  document.body.appendChild(overlay);

  // Element tag tooltip
  var tooltip = document.createElement('div');
  tooltip.style.cssText = 'position:fixed;z-index:2147483645;background:#1e1b4b;color:#e0e7ff;font:600 11px/1 monospace;padding:3px 7px;border-radius:3px;pointer-events:none;white-space:nowrap;display:none;box-shadow:0 2px 8px rgba(0,0,0,.3)';
  document.body.appendChild(tooltip);

  // Top banner / instructions
  var banner = document.createElement('div');
  banner.id = '__wm_banner__';
  banner.style.cssText = 'position:fixed;top:12px;left:50%;transform:translateX(-50%);z-index:2147483647;background:#1e1b4b;color:#e0e7ff;font:500 13px/1.4 system-ui,sans-serif;padding:10px 20px;border-radius:8px;box-shadow:0 4px 20px rgba(0,0,0,.3);pointer-events:none;white-space:nowrap';
  updateBanner();
  document.body.appendChild(banner);

  // "Pinned!" flash confirmation
  var flash = document.createElement('div');
  flash.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);z-index:2147483647;background:#059669;color:white;font:600 13px/1 system-ui,sans-serif;padding:8px 18px;border-radius:20px;pointer-events:none;opacity:0;transition:opacity 200ms ease;box-shadow:0 4px 12px rgba(0,0,0,.2)';
  document.body.appendChild(flash);

  function updateBanner() {
    if (limitReached) {
      banner.textContent = '✓ ' + pinMax + '/' + pinMax + ' elements selected — type your request in the panel  •  Esc to cancel';
      banner.style.background = '#064e3b';
    } else {
      banner.textContent = 'Click to pin an element (' + pinCount + '/' + pinMax + ')  •  Esc to cancel';
      banner.style.background = '#1e1b4b';
    }
  }

  function showFlash(msg) {
    flash.textContent = msg;
    flash.style.opacity = '1';
    setTimeout(function() { flash.style.opacity = '0'; }, 1600);
  }

  // ── Mouse handlers ────────────────────────────────────────────────────────
  function onMouseMove(e) {
    var el = e.target;
    if (!el || el === overlay || el === tooltip || el === banner || el === flash) return;
    var rect = el.getBoundingClientRect();
    overlay.style.display = 'block';
    overlay.style.top    = rect.top    + 'px';
    overlay.style.left   = rect.left   + 'px';
    overlay.style.width  = rect.width  + 'px';
    overlay.style.height = rect.height + 'px';
    var tag = el.tagName.toLowerCase();
    var cls = semanticClasses(el)[0];
    tooltip.textContent  = cls ? tag + '.' + cls : tag;
    tooltip.style.top    = Math.max(rect.top - 22, 4) + 'px';
    tooltip.style.left   = rect.left + 'px';
    tooltip.style.display = 'block';
  }

  function onClick(e) {
    if (limitReached) {
      showFlash('Limit reached — type your request in the panel');
      return;
    }
    e.preventDefault();
    e.stopImmediatePropagation();

    var el = e.target;
    if (!el || el === overlay || el === tooltip || el === banner || el === flash) return;

    var rect = el.getBoundingClientRect();
    var payload = {
      css_selector:    buildSelector(el),
      tag:             el.tagName.toLowerCase(),
      id:              el.id || null,
      classes:         Array.from(el.classList),
      text_content:    (el.textContent || '').trim().slice(0, 300),
      html:            el.outerHTML.slice(0, 600),
      dom_path:        buildDomPath(el),
      computed_styles: getStyles(el),
      bounding_box: {
        top:    Math.round(rect.top),
        left:   Math.round(rect.left),
        width:  Math.round(rect.width),
        height: Math.round(rect.height),
      },
      captured_at: new Date().toISOString(),
    };

    window.parent.postMessage({ type: 'WEBMAGIC_ELEMENT_SELECTED', payload: payload }, '*');
    // Parent will send WEBMAGIC_PIN_COUNT back; we optimistically increment for UX
    pinCount = Math.min(pinCount + 1, pinMax);
    updateBanner();
    showFlash('✓ Element pinned!');
  }

  function onKeyDown(e) {
    if (e.key === 'Escape') {
      window.parent.postMessage({ type: 'WEBMAGIC_INSPECTOR_CANCELLED' }, '*');
    }
  }

  // ── Listen for messages from parent ───────────────────────────────────────
  window.addEventListener('message', function(e) {
    var data = e.data;
    if (!data || !data.type) return;

    if (data.type === 'WEBMAGIC_PIN_COUNT') {
      pinCount = data.count;
      pinMax   = data.max;
      limitReached = (pinCount >= pinMax);
      updateBanner();
      if (limitReached) {
        document.body.style.cursor = 'not-allowed';
        overlay.style.border = '2px solid #059669';
      }
    }
  });

  // ── Activate ──────────────────────────────────────────────────────────────
  document.addEventListener('mousemove', onMouseMove, { passive: true });
  document.addEventListener('click', onClick, true);
  document.addEventListener('keydown', onKeyDown);
  document.body.style.cursor = 'crosshair';
})();
`
}
