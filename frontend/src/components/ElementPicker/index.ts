/**
 * ElementPicker — public API
 *
 * Visual element selection for support tickets.
 * Import from this barrel to keep imports clean in consuming components.
 */
export { ElementPickerOverlay } from './ElementPickerOverlay'
export { ElementPickerCard } from './ElementPickerCard'
export { useElementPicker, MAX_SELECTIONS } from './useElementPicker'
export type { ElementContext, CapturedStyles, BoundingBox } from './types'
