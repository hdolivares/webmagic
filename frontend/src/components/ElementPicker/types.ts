/**
 * ElementPicker Types
 *
 * Shared interfaces for the visual element selection feature.
 * This data is attached to site_edit tickets so the AI pipeline
 * has precise targeting information instead of guessing from prose.
 */

/** Subset of computed CSS properties we capture for LLM context. */
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

/** Geometric position within the page viewport. */
export interface BoundingBox {
  top: number
  left: number
  width: number
  height: number
}

/**
 * Full snapshot of a selected DOM element.
 * Serialised to JSON and stored in support_tickets.element_context.
 */
export interface ElementContext {
  /** Shortest reliable CSS selector, e.g. "section.hero > h1" */
  css_selector: string

  /** Tag name, e.g. "h1" */
  tag: string

  /** Element id attribute (if present) */
  id: string | null

  /** All class names on the element */
  classes: string[]

  /** Visible text content, truncated at 300 chars */
  text_content: string

  /** Outer HTML, truncated at 600 chars */
  html: string

  /** Human-readable ancestry breadcrumb, e.g. "body > section.hero > h1" */
  dom_path: string

  /** Key computed styles at the moment of capture */
  computed_styles: CapturedStyles

  /** Viewport-relative bounding box */
  bounding_box: BoundingBox

  /** ISO timestamp of when the element was picked */
  captured_at: string
}

/** Internal message shape sent via postMessage from iframe → parent. */
export interface InspectorMessage {
  type: 'WEBMAGIC_ELEMENT_SELECTED'
  payload: ElementContext
}
