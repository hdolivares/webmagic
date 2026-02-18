/**
 * SiteEditPanel
 *
 * Full-screen split-pane interface for creating site_edit tickets.
 * Left  (≈62%) — customer's live site in an iframe with the element inspector active.
 * Right (≈38%) — ticket form: subject, description, pinned element cards, submit.
 *
 * Design rationale:
 *   • Customers describe what to change while SEEING the site — no context switching.
 *   • Pinned elements give the AI precise CSS selectors + current styles.
 *   • Hard limit of 3 elements keeps ticket scope tight and LLM output focused.
 */
import React, { useState } from 'react'
import { ElementPickerCard } from '../ElementPicker'
import { useElementPicker, MAX_SELECTIONS } from '../ElementPicker/useElementPicker'
import type { ElementContext } from '../ElementPicker'
import './SiteEditPanel.css'

// ── Types ─────────────────────────────────────────────────────────────────

export interface SiteEditSubmitData {
  subject: string
  description: string
  element_context: ElementContext[] | null
}

interface SiteEditPanelProps {
  /** Public URL of the customer's site, e.g. https://web.lavish.solutions/my-site/ */
  siteUrl: string
  /** Human-readable site name for the header */
  siteName: string
  /** Called when the user submits — parent handles the API call */
  onSubmit: (data: SiteEditSubmitData) => Promise<void>
  /** Called when the user cancels */
  onClose: () => void
}

// ── Component ─────────────────────────────────────────────────────────────

export function SiteEditPanel({ siteUrl, siteName, onSubmit, onClose }: SiteEditPanelProps) {
  const [subject, setSubject] = useState('')
  const [description, setDescription] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const {
    selectedElements,
    canAddMore,
    removeElement,
    clearAll,
    iframeRef,
  } = useElementPicker()

  // ── Auto-inject inspector when iframe loads ──────────────────────────────
  // The hook handles injection; we just need to keep the iframe mounted.

  // ── Submission ────────────────────────────────────────────────────────────
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!subject.trim() || subject.trim().length < 5) {
      setError('Subject must be at least 5 characters.')
      return
    }
    if (!description.trim() || description.trim().length < 10) {
      setError('Description must be at least 10 characters.')
      return
    }

    setError(null)
    setSubmitting(true)
    try {
      await onSubmit({
        subject: subject.trim(),
        description: description.trim(),
        element_context: selectedElements.length > 0 ? selectedElements : null,
      })
    } catch (err: any) {
      setError(err?.message ?? 'Failed to submit. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  // ── Derived state ─────────────────────────────────────────────────────────
  const pinCount = selectedElements.length
  const atLimit = pinCount >= MAX_SELECTIONS
  const canSubmit = subject.trim().length >= 5 && description.trim().length >= 10 && !submitting

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="site-edit-panel" role="dialog" aria-modal="true" aria-label="Site edit ticket">

      {/* ── Global header ───────────────────────────────────────────── */}
      <header className="site-edit-panel__header">
        <div className="site-edit-panel__header-left">
          <span className="site-edit-panel__header-icon" aria-hidden="true">✏️</span>
          <div>
            <strong className="site-edit-panel__header-title">Site Edit Request</strong>
            <span className="site-edit-panel__header-site">{siteName}</span>
          </div>
        </div>

        <button
          type="button"
          className="site-edit-panel__close"
          onClick={onClose}
          aria-label="Cancel and close"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
          Cancel
        </button>
      </header>

      {/* ── Content: two-column ─────────────────────────────────────── */}
      <div className="site-edit-panel__body">

        {/* LEFT — site iframe ─────────────────────────────────────── */}
        <section className="site-edit-panel__site" aria-label="Your website">
          {canAddMore ? (
            <div className="site-edit-panel__site-hint">
              <span>🎯</span>
              <span>
                {pinCount === 0
                  ? 'Click any element to pin it to your request'
                  : `${pinCount}/${MAX_SELECTIONS} pinned — click more or describe your request →`}
              </span>
            </div>
          ) : (
            <div className="site-edit-panel__site-hint site-edit-panel__site-hint--done">
              <span>✅</span>
              <span>{MAX_SELECTIONS}/{MAX_SELECTIONS} elements pinned — now describe your request →</span>
            </div>
          )}

          <iframe
            ref={iframeRef}
            src={siteUrl}
            className="site-edit-panel__iframe"
            title="Your website"
            sandbox="allow-scripts allow-same-origin"
          />
        </section>

        {/* RIGHT — ticket form ────────────────────────────────────── */}
        <aside className="site-edit-panel__form-col" aria-label="Ticket details">
          <form className="site-edit-panel__form" onSubmit={handleSubmit} noValidate>

            {/* Subject */}
            <div className="site-edit-panel__field">
              <label className="site-edit-panel__label" htmlFor="sep-subject">
                Subject <span className="site-edit-panel__required">*</span>
              </label>
              <input
                id="sep-subject"
                type="text"
                className="site-edit-panel__input"
                value={subject}
                onChange={e => setSubject(e.target.value)}
                placeholder="e.g. Change hero background color"
                minLength={5}
                maxLength={255}
                disabled={submitting}
                required
              />
            </div>

            {/* Description */}
            <div className="site-edit-panel__field site-edit-panel__field--grow">
              <label className="site-edit-panel__label" htmlFor="sep-desc">
                Describe the change <span className="site-edit-panel__required">*</span>
              </label>
              <textarea
                id="sep-desc"
                className="site-edit-panel__textarea"
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="Describe what you'd like changed in plain language — no technical knowledge needed…"
                minLength={10}
                disabled={submitting}
                required
              />
              <p className="site-edit-panel__hint-text">
                Be as descriptive as you like. The AI will use your pinned elements + this description
                to understand exactly what to change.
              </p>
            </div>

            {/* Pinned elements ──────────────────────────────────── */}
            <div className="site-edit-panel__pins">
              <div className="site-edit-panel__pins-header">
                <span className="site-edit-panel__pins-label">
                  📌 Pinned elements
                </span>
                <span
                  className={`site-edit-panel__pins-counter ${atLimit ? 'site-edit-panel__pins-counter--full' : ''}`}
                >
                  {pinCount}/{MAX_SELECTIONS}
                </span>
                {pinCount > 0 && (
                  <button
                    type="button"
                    className="site-edit-panel__pins-clear"
                    onClick={clearAll}
                    disabled={submitting}
                  >
                    Clear all
                  </button>
                )}
              </div>

              {selectedElements.length === 0 ? (
                <p className="site-edit-panel__pins-empty">
                  Click elements on your site (left) to pin them here.
                  This is optional — you can also just describe the change in words.
                </p>
              ) : (
                <div className="site-edit-panel__pins-list">
                  {selectedElements.map((el, idx) => (
                    <div key={idx} className="site-edit-panel__pin-wrapper">
                      <span className="site-edit-panel__pin-number">{idx + 1}</span>
                      <div className="site-edit-panel__pin-card">
                        <ElementPickerCard
                          element={el}
                          onRemove={() => removeElement(idx)}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {!atLimit && pinCount > 0 && (
                <p className="site-edit-panel__pins-more">
                  You can pin {MAX_SELECTIONS - pinCount} more element{MAX_SELECTIONS - pinCount !== 1 ? 's' : ''}.
                </p>
              )}
            </div>

            {/* Error */}
            {error && (
              <div className="site-edit-panel__error" role="alert">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                {error}
              </div>
            )}

            {/* Actions */}
            <div className="site-edit-panel__actions">
              <button
                type="button"
                className="site-edit-panel__btn site-edit-panel__btn--secondary"
                onClick={onClose}
                disabled={submitting}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="site-edit-panel__btn site-edit-panel__btn--primary"
                disabled={!canSubmit}
              >
                {submitting ? (
                  <>
                    <span className="site-edit-panel__spinner" aria-hidden="true" />
                    Submitting…
                  </>
                ) : (
                  <>
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
                      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="22" y1="2" x2="11" y2="13" />
                      <polygon points="22 2 15 22 11 13 2 9 22 2" />
                    </svg>
                    Submit Request
                  </>
                )}
              </button>
            </div>

          </form>
        </aside>
      </div>
    </div>
  )
}
