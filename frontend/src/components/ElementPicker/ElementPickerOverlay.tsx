/**
 * ElementPickerOverlay
 *
 * Renders the customer's website inside a full-screen iframe overlay.
 * The inspector script (injected on load) handles hover highlighting
 * and click capture; results are postMessaged back to the parent.
 */
import React from 'react'
import './ElementPickerOverlay.css'

interface ElementPickerOverlayProps {
  siteUrl: string
  iframeRef: React.RefObject<HTMLIFrameElement>
  onClose: () => void
}

export function ElementPickerOverlay({
  siteUrl,
  iframeRef,
  onClose,
}: ElementPickerOverlayProps) {
  return (
    <div className="picker-overlay" role="dialog" aria-modal="true" aria-label="Select an element on your site">
      {/* ── Top toolbar ───────────────────────────────────────────────── */}
      <header className="picker-overlay__toolbar">
        <div className="picker-overlay__toolbar-left">
          <span className="picker-overlay__icon" aria-hidden="true">🎯</span>
          <div className="picker-overlay__instructions">
            <strong>Click any element on your site</strong>
            <span>to pin it to your ticket — or press Esc to cancel</span>
          </div>
        </div>

        <button
          className="picker-overlay__close"
          onClick={onClose}
          aria-label="Cancel element selection"
          type="button"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
          Cancel
        </button>
      </header>

      {/* ── Site iframe ───────────────────────────────────────────────── */}
      <iframe
        ref={iframeRef}
        src={siteUrl}
        className="picker-overlay__iframe"
        title="Your website — click to select an element"
        sandbox="allow-scripts allow-same-origin"
      />
    </div>
  )
}
