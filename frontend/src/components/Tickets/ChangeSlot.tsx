/**
 * ChangeSlot
 *
 * One self-contained change request row.
 * Pairs a plain-language description with an optional pinned element.
 * Designed to be rendered inside SiteEditPanel's right panel.
 */
import type { ElementContext, TicketChange } from '../ElementPicker/types'
import { ElementPickerCard } from '../ElementPicker/ElementPickerCard'
import './ChangeSlot.css'

interface ChangeSlotProps {
  index: number
  change: TicketChange

  /** True when this slot is waiting to receive a click from the site iframe */
  isActive: boolean

  /** Whether to show the Remove button (hidden when there is only one slot) */
  canRemove: boolean

  onActivate: () => void
  onDeactivate: () => void
  onDescriptionChange: (text: string) => void
  onClearElement: () => void
  onRemove: () => void
}

export function ChangeSlot({
  index,
  change,
  isActive,
  canRemove,
  onActivate,
  onDeactivate,
  onDescriptionChange,
  onClearElement,
  onRemove,
}: ChangeSlotProps) {
  return (
    <div className={`change-slot ${isActive ? 'change-slot--active' : ''}`}>
      {/* ── Header ── */}
      <div className="change-slot__header">
        <span className="change-slot__badge">Change {index + 1}</span>
        {isActive && (
          <span className="change-slot__active-hint">🎯 Click an element on the site</span>
        )}
        {canRemove && (
          <button
            type="button"
            className="change-slot__remove"
            aria-label={`Remove change ${index + 1}`}
            onClick={onRemove}
          >
            ✕
          </button>
        )}
      </div>

      {/* ── Description textarea ── */}
      <textarea
        className="change-slot__description"
        rows={3}
        placeholder={`What would you like changed? (Change ${index + 1})`}
        value={change.description}
        onChange={e => onDescriptionChange(e.target.value)}
      />

      {/* ── Pin area ── */}
      <div className="change-slot__pin-area">
        {change.element ? (
          <PinnedElementPreview
            element={change.element}
            slotLabel={`Change ${index + 1}`}
            isActive={isActive}
            onReplace={onActivate}
            onClear={onClearElement}
          />
        ) : (
          <PinButton isActive={isActive} onActivate={onActivate} onDeactivate={onDeactivate} />
        )}
      </div>
    </div>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────────

function PinButton({
  isActive,
  onActivate,
  onDeactivate,
}: {
  isActive: boolean
  onActivate: () => void
  onDeactivate: () => void
}) {
  if (isActive) {
    return (
      <button
        type="button"
        className="change-slot__pin-btn change-slot__pin-btn--active"
        onClick={onDeactivate}
      >
        <span className="change-slot__pin-pulse" />
        Pinning… click any element on the site to the left
      </button>
    )
  }

  return (
    <button
      type="button"
      className="change-slot__pin-btn"
      onClick={onActivate}
    >
      📌 Pin a specific element <span className="change-slot__optional">(optional)</span>
    </button>
  )
}

function PinnedElementPreview({
  element,
  slotLabel,
  isActive,
  onReplace,
  onClear,
}: {
  element: ElementContext
  slotLabel: string
  isActive: boolean
  onReplace: () => void
  onClear: () => void
}) {
  return (
    <div className="change-slot__pinned-element">
      <ElementPickerCard element={element} onRemove={onClear} />
      <button
        type="button"
        className={`change-slot__replace-btn ${isActive ? 'change-slot__replace-btn--active' : ''}`}
        onClick={onReplace}
      >
        {isActive ? '🎯 Click new element…' : '↺ Replace pin'}
      </button>
    </div>
  )
}
