/**
 * SiteEditPanel
 *
 * Full-screen split-pane interface for creating site_edit tickets.
 *
 *   Left  (≈62%) — customer's live site in an iframe with the element inspector
 *   Right (≈38%) — structured change slots: each slot has its own description
 *                   and an optional pinned element
 *
 * Data flow:
 *   useElementPicker → lastCaptured → SiteEditPanel routes to active slot
 *   useTicketChanges → manages change array (add/remove/update/pin)
 *   ChangeSlot       → renders one (description + optional pin) row
 */
import React, { useEffect, useState } from 'react'
import { useElementPicker } from '../ElementPicker/useElementPicker'
import { useTicketChanges, MAX_CHANGES } from './useTicketChanges'
import { ChangeSlot } from './ChangeSlot'
import type { TicketChange } from '../ElementPicker/types'
import './SiteEditPanel.css'

// ── Public types ───────────────────────────────────────────────────────────

export interface SiteEditSubmitData {
  /** Auto-generated from first change description */
  subject: string
  /** Combined plain-text summary for the description field */
  description: string
  /** Structured per-change data sent to the backend */
  changes: TicketChange[]
}

interface SiteEditPanelProps {
  /** Public URL of the customer's site */
  siteUrl: string
  /** Human-readable site name for the header */
  siteName: string
  /** Called when the user submits — parent handles the API call */
  onSubmit: (data: SiteEditSubmitData) => Promise<void>
  /** Called when the user cancels */
  onClose: () => void
}

// ── Component ──────────────────────────────────────────────────────────────

export function SiteEditPanel({ siteUrl, siteName, onSubmit, onClose }: SiteEditPanelProps) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // ── Hooks ──────────────────────────────────────────────────────────────────
  const {
    iframeRef,
    lastCaptured,
    clearLastCaptured,
    announceActiveSlot,
    announceSlotCount,
  } = useElementPicker({
    onCancel: onClose,
    // Auto-activate the first slot AFTER the inspector is ready.
    // Doing it here (not on mount) guarantees the WEBMAGIC_ACTIVE_SLOT
    // message arrives after the inspector's listener is registered.
    onReady: () => setActiveChange(changes[0]?.id ?? null),
  })

  const {
    changes,
    activeChangeId,
    setActiveChange,
    addChange,
    removeChange,
    updateDescription,
    pinElementToActive,
    clearElement,
    canAddMore,
    pinnedCount,
    isValid,
  } = useTicketChanges()

  // ── Route captured element to active slot ──────────────────────────────────
  useEffect(() => {
    if (lastCaptured && activeChangeId) {
      pinElementToActive(lastCaptured)
      clearLastCaptured()
    }
  }, [lastCaptured, activeChangeId, pinElementToActive, clearLastCaptured])

  // ── Keep iframe banner in sync with active slot ────────────────────────────
  useEffect(() => {
    if (!activeChangeId) {
      announceActiveSlot(null)
      return
    }
    const idx = changes.findIndex(c => c.id === activeChangeId)
    announceActiveSlot(idx >= 0 ? `Change ${idx + 1}` : null)
  }, [activeChangeId, changes, announceActiveSlot])

  // ── Keep iframe pin count badge in sync ────────────────────────────────────
  useEffect(() => {
    announceSlotCount(pinnedCount, MAX_CHANGES)
  }, [pinnedCount, announceSlotCount])

  // ── Deactivate active slot when its element is pinned ─────────────────────
  // (pinElementToActive already clears activeChangeId via setActiveChange(null))

  // ── Submission ────────────────────────────────────────────────────────────
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!isValid) {
      setError('Each change must have a description of at least 5 characters.')
      return
    }

    const subject = buildSubject(changes)
    const description = buildDescription(changes)

    setError(null)
    setSubmitting(true)
    try {
      await onSubmit({ subject, description, changes })
    } catch (err: any) {
      setError(err?.message ?? 'Failed to submit. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const canSubmit = isValid && !submitting

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="site-edit-panel" role="dialog" aria-modal="true" aria-label="Site edit ticket">

      {/* ── Header ────────────────────────────────────────────────────── */}
      <header className="site-edit-panel__header">
        <div className="site-edit-panel__header-left">
          <span aria-hidden="true">✏️</span>
          <div>
            <strong className="site-edit-panel__header-title">Site Edit Request</strong>
            <span className="site-edit-panel__header-site">{siteName}</span>
          </div>
        </div>

        <div className="site-edit-panel__header-right">
          <span className="site-edit-panel__change-count">
            {changes.length}/{MAX_CHANGES} change{changes.length !== 1 ? 's' : ''}
            {pinnedCount > 0 && ` · ${pinnedCount} pinned`}
          </span>
          <button
            type="button"
            className="site-edit-panel__close"
            onClick={onClose}
            aria-label="Cancel and close"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
            Cancel
          </button>
        </div>
      </header>

      {/* ── Body: two-column ──────────────────────────────────────────── */}
      <div className="site-edit-panel__body">

        {/* LEFT — site iframe ─────────────────────────────────────────── */}
        <section className="site-edit-panel__site" aria-label="Your website">
          <iframe
            ref={iframeRef}
            src={siteUrl}
            className="site-edit-panel__iframe"
            title="Your website"
            sandbox="allow-scripts allow-same-origin"
          />
        </section>

        {/* RIGHT — change slots ────────────────────────────────────────── */}
        <aside className="site-edit-panel__form-col" aria-label="Ticket details">
          <form className="site-edit-panel__form" onSubmit={handleSubmit} noValidate>

            <p className="site-edit-panel__intro">
              Describe each change you need. Optionally click "Pin element" and then click
              on a specific area of your site to give the AI exact context.
            </p>

            {/* Change slots */}
            <div className="site-edit-panel__slots">
              {changes.map((change, idx) => (
                <ChangeSlot
                  key={change.id}
                  index={idx}
                  change={change}
                  isActive={change.id === activeChangeId}
                  canRemove={changes.length > 1}
                  onActivate={() => setActiveChange(change.id)}
                  onDeactivate={() => setActiveChange(null)}
                  onDescriptionChange={text => updateDescription(change.id, text)}
                  onClearElement={() => clearElement(change.id)}
                  onRemove={() => removeChange(change.id)}
                />
              ))}
            </div>

            {/* Add change button */}
            {canAddMore && (
              <button
                type="button"
                className="site-edit-panel__add-change"
                onClick={addChange}
                disabled={submitting}
              >
                + Add another change
                <span className="site-edit-panel__add-hint">
                  ({MAX_CHANGES - changes.length} remaining)
                </span>
              </button>
            )}

            {/* Error */}
            {error && (
              <div className="site-edit-panel__error" role="alert">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
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
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
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

// ── Pure helpers ──────────────────────────────────────────────────────────

function buildSubject(changes: TicketChange[]): string {
  const first = changes[0]?.description?.trim() ?? ''
  const truncated = first.length > 80 ? first.slice(0, 80) + '…' : first
  if (changes.length === 1) return truncated
  return `${truncated} (+${changes.length - 1} more change${changes.length > 2 ? 's' : ''})`
}

function buildDescription(changes: TicketChange[]): string {
  return changes
    .map((c, i) => {
      const header = `Change ${i + 1}: ${c.description.trim()}`
      const pin = c.element
        ? `\nTarget element: ${c.element.css_selector} (${c.element.tag}${c.element.id ? `#${c.element.id}` : ''})`
        : ''
      return header + pin
    })
    .join('\n\n')
}
