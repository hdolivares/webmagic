/**
 * ElementPickerCard
 *
 * Displays the captured element as a compact, dismissible annotation
 * within the ticket form. Shows:
 *   • CSS selector (the "address" of the element)
 *   • Text content preview
 *   • Key visual properties (font-size, color, background)
 *   • A remove button to clear the selection
 */
import React from 'react'
import type { ElementContext } from './types'
import './ElementPickerCard.css'

interface ElementPickerCardProps {
  element: ElementContext
  onRemove: () => void
}

/** Render a single style property pill when it carries useful information. */
function StylePill({ label, value }: { label: string; value: string }) {
  // Don't show defaults like "0px" padding or "rgba(0,0,0,0)" backgrounds
  const isDefault =
    value === '0px' || value === 'normal' || value === 'rgba(0, 0, 0, 0)' || value === 'auto'

  if (isDefault || !value) return null

  return (
    <span className="picker-card__style-pill">
      <span className="picker-card__style-label">{label}</span>
      <span className="picker-card__style-value">{value}</span>
    </span>
  )
}

/** Colour swatch rendered next to a colour value, for quick visual confirmation. */
function ColorSwatch({ color }: { color: string }) {
  if (!color || color === 'rgba(0, 0, 0, 0)') return null
  return (
    <span
      className="picker-card__color-swatch"
      style={{ background: color }}
      aria-hidden="true"
    />
  )
}

export function ElementPickerCard({ element, onRemove }: ElementPickerCardProps) {
  const { tag, css_selector, text_content, computed_styles, dom_path } = element

  const fontSize = computed_styles['font-size']
  const fontWeight = computed_styles['font-weight']
  const color = computed_styles['color']
  const bgColor = computed_styles['background-color']

  return (
    <div className="picker-card" role="region" aria-label="Selected element annotation">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="picker-card__header">
        <div className="picker-card__header-left">
          <span className="picker-card__pin-icon" aria-hidden="true">📌</span>
          <div className="picker-card__title-group">
            <span className="picker-card__tag-badge">&lt;{tag}&gt;</span>
            <span className="picker-card__label">Element selected</span>
          </div>
        </div>

        <button
          type="button"
          className="picker-card__remove"
          onClick={onRemove}
          aria-label="Remove element selection"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      {/* ── Selector ────────────────────────────────────────────────────── */}
      <div className="picker-card__selector" title={css_selector}>
        <code>{css_selector}</code>
      </div>

      {/* ── Text preview ────────────────────────────────────────────────── */}
      {text_content && (
        <p className="picker-card__text-preview">
          &ldquo;{text_content.length > 120 ? text_content.slice(0, 117) + '…' : text_content}&rdquo;
        </p>
      )}

      {/* ── Computed styles ─────────────────────────────────────────────── */}
      <div className="picker-card__styles">
        <StylePill label="font-size" value={fontSize} />
        <StylePill label="font-weight" value={fontWeight} />

        {color && color !== 'rgba(0, 0, 0, 0)' && (
          <span className="picker-card__style-pill">
            <span className="picker-card__style-label">color</span>
            <ColorSwatch color={color} />
            <span className="picker-card__style-value">{color}</span>
          </span>
        )}

        {bgColor && bgColor !== 'rgba(0, 0, 0, 0)' && (
          <span className="picker-card__style-pill">
            <span className="picker-card__style-label">bg</span>
            <ColorSwatch color={bgColor} />
            <span className="picker-card__style-value">{bgColor}</span>
          </span>
        )}
      </div>

      {/* ── DOM path breadcrumb ─────────────────────────────────────────── */}
      <p className="picker-card__dom-path" title={dom_path}>{dom_path}</p>

      <p className="picker-card__hint">
        This element's details will be shared with our team so we know exactly what to update.
      </p>
    </div>
  )
}
