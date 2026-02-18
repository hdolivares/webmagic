/**
 * Inspector Script — injected verbatim into the customer's site iframe.
 *
 * Responsibilities:
 *   • Highlight DOM elements on hover (CSS outline overlay)
 *   • On click: capture element metadata (selector, styles, geometry, HTML)
 *   • postMessage the capture back to the parent window
 *
 * Constraints:
 *   • Zero external dependencies — runs in the iframe with no bundler
 *   • Must be a self-contained IIFE string
 *   • Must not interfere with the site's own JS (uses a prefixed namespace)
 */

/**
 * Utility classes whose names carry no semantic meaning.
 * We filter these out when building CSS selectors so the selector
 * reads as "section.hero > h1" rather than "div.flex.items-center > h1".
 */
const UTILITY_CLASS_PATTERN =
  /^(flex|grid|block|inline|hidden|absolute|relative|fixed|sticky|overflow|container|wrapper|row|col(?:umn)?-?\d*|d-|is-|js-|text-(?:xs|sm|base|lg|xl|2xl|3xl|4xl|5xl|6xl|7xl|8xl|9xl|left|right|center|justify)|bg-|p-|px-|py-|pt-|pb-|pl-|pr-|m-|mx-|my-|mt-|mb-|ml-|mr-|w-|h-|min-[wh]-|max-[wh]-|border(?:-\w+)?|rounded(?:-\w+)?|shadow(?:-\w+)?|font-(?:thin|light|normal|medium|semibold|bold|extrabold|black|\d{3})|leading-|tracking-|items-|justify-|gap-|space-[xy]-|z-\d|opacity-|cursor-|select-|sr-only|not-sr-only|\d+)/

/**
 * Build a concise, human-readable CSS selector for a DOM element.
 * Prefers: #id → .semantic-class path → tag:nth-child path.
 * Stops at 5 ancestor levels or the first id anchor.
 */
function buildSelector(el: Element): string {
  const segments: string[] = []
  let node: Element | null = el

  for (let depth = 0; depth < 6 && node && node.tagName; depth++) {
    // ID is globally unique — anchor here and stop
    if (node.id) {
      segments.unshift('#' + node.id)
      break
    }

    const tag = node.tagName.toLowerCase()

    // Collect semantic (non-utility) classes, prefer longer names
    const semanticClasses = Array.from(node.classList)
      .filter(c => c.length > 2 && !UTILITY_CLASS_PATTERN.test(c))
      .sort((a, b) => b.length - a.length)
      .slice(0, 2)

    let segment = tag
    if (semanticClasses.length > 0) {
      segment += '.' + semanticClasses.join('.')
    }

    // Disambiguate siblings of the same type when no unique class
    if (semanticClasses.length === 0 && node.parentElement) {
      const siblings = Array.from(node.parentElement.children).filter(
        s => s.tagName === node!.tagName,
      )
      if (siblings.length > 1) {
        const allChildren = Array.from(node.parentElement.children)
        segment += `:nth-child(${allChildren.indexOf(node) + 1})`
      }
    }

    segments.unshift(segment)
    node = node.parentElement
  }

  return segments.join(' > ')
}

/** Build the ancestry breadcrumb shown in the UI, e.g. "body > section.hero > h1" */
function buildDomPath(el: Element): string {
  const crumbs: string[] = []
  let node: Element | null = el

  for (let depth = 0; depth < 5 && node && node.tagName; depth++) {
    const tag = node.tagName.toLowerCase()
    const cls = Array.from(node.classList)
      .filter(c => !UTILITY_CLASS_PATTERN.test(c))
      .slice(0, 1)[0]
    crumbs.unshift(node.id ? `${tag}#${node.id}` : cls ? `${tag}.${cls}` : tag)
    node = node.parentElement
  }

  return crumbs.join(' > ')
}

/** CSS property names we extract from getComputedStyle */
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

/**
 * Serialise the self-contained inspector IIFE as a string.
 * Called once; the result is injected via a <script> element inside the iframe.
 */
export function buildInspectorScript(): string {
  // Capture constants and helpers as strings to embed in the IIFE
  const utilityPattern = UTILITY_CLASS_PATTERN.source
  const styleKeys = JSON.stringify(STYLE_KEYS)

  return /* javascript */ `
(function () {
  'use strict';

  // ── Config ────────────────────────────────────────────────────────────────
  var UTILITY_RE = new RegExp(${JSON.stringify(utilityPattern)});
  var STYLE_KEYS = ${styleKeys};
  var ORIGIN = window.location.origin;

  // ── Highlight overlay ─────────────────────────────────────────────────────
  var overlay = document.createElement('div');
  overlay.id = '__wm_inspector_overlay__';
  overlay.style.cssText = [
    'position:fixed',
    'pointer-events:none',
    'z-index:2147483647',
    'box-sizing:border-box',
    'border:2px solid #6366f1',
    'background:rgba(99,102,241,0.08)',
    'border-radius:3px',
    'transition:all 80ms ease',
    'display:none',
  ].join(';');
  document.body.appendChild(overlay);

  // Tooltip showing element tag + class
  var tooltip = document.createElement('div');
  tooltip.id = '__wm_inspector_tooltip__';
  tooltip.style.cssText = [
    'position:fixed',
    'z-index:2147483647',
    'background:#1e1b4b',
    'color:#e0e7ff',
    'font:600 11px/1 monospace',
    'padding:3px 7px',
    'border-radius:3px',
    'pointer-events:none',
    'white-space:nowrap',
    'display:none',
    'box-shadow:0 2px 8px rgba(0,0,0,0.3)',
  ].join(';');
  document.body.appendChild(tooltip);

  // Exit hint banner
  var banner = document.createElement('div');
  banner.style.cssText = [
    'position:fixed',
    'top:12px',
    'left:50%',
    'transform:translateX(-50%)',
    'z-index:2147483647',
    'background:#1e1b4b',
    'color:#e0e7ff',
    'font:500 13px/1.4 system-ui,sans-serif',
    'padding:10px 20px',
    'border-radius:8px',
    'box-shadow:0 4px 20px rgba(0,0,0,0.3)',
    'pointer-events:none',
  ].join(';');
  banner.textContent = 'Click any element to select it  •  Press Esc to cancel';
  document.body.appendChild(banner);

  // ── Helpers ───────────────────────────────────────────────────────────────
  function semanticClasses(el) {
    return Array.from(el.classList)
      .filter(function(c) { return c.length > 2 && !UTILITY_RE.test(c); })
      .sort(function(a, b) { return b.length - a.length; })
      .slice(0, 2);
  }

  function buildSelector(el) {
    var segments = [];
    var node = el;
    for (var depth = 0; depth < 6 && node && node.tagName; depth++) {
      if (node.id) { segments.unshift('#' + node.id); break; }
      var tag = node.tagName.toLowerCase();
      var cls = semanticClasses(node);
      var seg = tag + (cls.length ? '.' + cls.join('.') : '');
      if (!cls.length && node.parentElement) {
        var sibs = Array.from(node.parentElement.children).filter(function(s) {
          return s.tagName === node.tagName;
        });
        if (sibs.length > 1) {
          var all = Array.from(node.parentElement.children);
          seg += ':nth-child(' + (all.indexOf(node) + 1) + ')';
        }
      }
      segments.unshift(seg);
      node = node.parentElement;
    }
    return segments.join(' > ');
  }

  function buildDomPath(el) {
    var crumbs = [];
    var node = el;
    for (var d = 0; d < 5 && node && node.tagName; d++) {
      var tag = node.tagName.toLowerCase();
      var cls = Array.from(node.classList).filter(function(c) {
        return !UTILITY_RE.test(c);
      })[0];
      crumbs.unshift(node.id ? tag + '#' + node.id : cls ? tag + '.' + cls : tag);
      node = node.parentElement;
    }
    return crumbs.join(' > ');
  }

  function getStyles(el) {
    var cs = window.getComputedStyle(el);
    var result = {};
    STYLE_KEYS.forEach(function(k) { result[k] = cs.getPropertyValue(k).trim(); });
    return result;
  }

  // ── Mouse handlers ────────────────────────────────────────────────────────
  function onMouseMove(e) {
    var el = e.target;
    if (!el || el === overlay || el === tooltip || el === banner) return;
    var rect = el.getBoundingClientRect();
    overlay.style.cssText += (
      ';display:block' +
      ';top:' + rect.top + 'px' +
      ';left:' + rect.left + 'px' +
      ';width:' + rect.width + 'px' +
      ';height:' + rect.height + 'px'
    );
    var tag = el.tagName.toLowerCase();
    var cls = semanticClasses(el).slice(0, 1)[0];
    tooltip.textContent = cls ? tag + '.' + cls : tag;
    tooltip.style.top = Math.max(rect.top - 22, 4) + 'px';
    tooltip.style.left = rect.left + 'px';
    tooltip.style.display = 'block';
  }

  function onClick(e) {
    e.preventDefault();
    e.stopImmediatePropagation();
    var el = e.target;
    if (!el || el === overlay || el === tooltip || el === banner) return;

    var rect = el.getBoundingClientRect();
    var payload = {
      css_selector: buildSelector(el),
      tag: el.tagName.toLowerCase(),
      id: el.id || null,
      classes: Array.from(el.classList),
      text_content: (el.textContent || '').trim().slice(0, 300),
      html: el.outerHTML.slice(0, 600),
      dom_path: buildDomPath(el),
      computed_styles: getStyles(el),
      bounding_box: {
        top: Math.round(rect.top),
        left: Math.round(rect.left),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      },
      captured_at: new Date().toISOString(),
    };

    window.parent.postMessage(
      { type: 'WEBMAGIC_ELEMENT_SELECTED', payload: payload },
      '*'
    );
  }

  function onKeyDown(e) {
    if (e.key === 'Escape') {
      window.parent.postMessage({ type: 'WEBMAGIC_INSPECTOR_CANCELLED' }, '*');
    }
  }

  // ── Activate ──────────────────────────────────────────────────────────────
  document.addEventListener('mousemove', onMouseMove, { passive: true });
  document.addEventListener('click', onClick, true);
  document.addEventListener('keydown', onKeyDown);
  document.body.style.cursor = 'crosshair';
})();
`
}
