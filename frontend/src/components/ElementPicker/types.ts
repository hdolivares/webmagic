/**
 * ElementPicker Types
 *
 * Shared data contracts for the visual element selection and
 * structured ticket change system.
 */

// ── Element snapshot ───────────────────────────────────────────────────────

/** Subset of computed CSS properties captured for LLM context. */
export interface CapturedStyles {
  'font-size': string
  'font-weight': string
  'font-family': string
  color: string
  'background-color': string
  padding: string
  margin: string
  display: string
  'text-align'?: string
  'border-radius'?: string
}

/** Viewport-relative geometry. */
export interface BoundingBox {
  top: number
  left: number
  width: number
  height: number
}

/**
 * Full DOM element snapshot captured by the inspector.
 * Stored per-change in support_tickets.element_context JSONB.
 */
export interface ElementContext {
  css_selector: string
  tag: string
  id: string | null
  classes: string[]
  text_content: string
  html: string
  dom_path: string
  computed_styles: CapturedStyles
  bounding_box: BoundingBox
  captured_at: string
}

// ── Ticket change ──────────────────────────────────────────────────────────

/**
 * A single, self-contained change request.
 * Pairing one plain-language description with one optional pinned element
 * gives Stage 2 zero-ambiguity targeting — no cross-referencing required.
 */
export interface TicketChange {
  /** Client-side unique id (crypto.randomUUID) */
  id: string
  /** Customer's plain-language description of what to change */
  description: string
  /** The exact DOM element to target, or null if not pinned */
  element: ElementContext | null
}

// ── postMessage contracts ──────────────────────────────────────────────────

/** Sent from iframe → parent when an element is clicked. */
export interface InspectorMessage {
  type: 'WEBMAGIC_ELEMENT_SELECTED'
  payload: ElementContext
}
