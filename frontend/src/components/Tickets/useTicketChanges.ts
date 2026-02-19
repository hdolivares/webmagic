/**
 * useTicketChanges
 *
 * Single-responsibility hook: manages the ordered list of ticket changes.
 *
 * Each change is an (description, optional element) pair.
 * The hook does NOT know about the iframe or the element picker —
 * the parent component wires them together.
 */
import { useCallback, useState } from 'react'
import type { ElementContext, TicketChange } from '../ElementPicker/types'

export const MAX_CHANGES = 3

interface UseTicketChangesReturn {
  /** Ordered list of change slots (always at least 1) */
  changes: TicketChange[]

  /** ID of the slot currently accepting a pinned element; null = none */
  activeChangeId: string | null

  /** Make a slot the active pin target (set null to deactivate) */
  setActiveChange: (id: string | null) => void

  /** Append a new empty slot (no-op when at MAX_CHANGES) */
  addChange: () => void

  /** Remove a slot by id (minimum 1 slot is always kept) */
  removeChange: (id: string) => void

  /** Update the description of a slot */
  updateDescription: (id: string, text: string) => void

  /** Pin an element to the currently active slot, then clear activeChangeId */
  pinElementToActive: (element: ElementContext) => void

  /** Detach the pinned element from a slot */
  clearElement: (id: string) => void

  /** Whether another slot can be added */
  canAddMore: boolean

  /** Number of slots that have a pinned element */
  pinnedCount: number

  /** Whether all changes have at least a non-empty description */
  isValid: boolean
}

function makeChange(): TicketChange {
  return { id: crypto.randomUUID(), description: '', element: null }
}

export function useTicketChanges(): UseTicketChangesReturn {
  const [changes, setChanges] = useState<TicketChange[]>([makeChange()])
  const [activeChangeId, setActiveChangeId] = useState<string | null>(null)

  const addChange = useCallback(() => {
    setChanges(prev => {
      if (prev.length >= MAX_CHANGES) return prev
      return [...prev, makeChange()]
    })
  }, [])

  const removeChange = useCallback(
    (id: string) => {
      setChanges(prev => {
        if (prev.length <= 1) return prev
        return prev.filter(c => c.id !== id)
      })
      setActiveChangeId(prev => (prev === id ? null : prev))
    },
    [],
  )

  const updateDescription = useCallback((id: string, text: string) => {
    setChanges(prev => prev.map(c => (c.id === id ? { ...c, description: text } : c)))
  }, [])

  const pinElementToActive = useCallback(
    (element: ElementContext) => {
      if (!activeChangeId) return
      setChanges(prev =>
        prev.map(c => (c.id === activeChangeId ? { ...c, element } : c)),
      )
      setActiveChangeId(null)
    },
    [activeChangeId],
  )

  const clearElement = useCallback((id: string) => {
    setChanges(prev => prev.map(c => (c.id === id ? { ...c, element: null } : c)))
  }, [])

  const setActiveChange = useCallback((id: string | null) => {
    setActiveChangeId(id)
  }, [])

  const canAddMore = changes.length < MAX_CHANGES
  const pinnedCount = changes.filter(c => c.element !== null).length
  const isValid = changes.every(c => c.description.trim().length >= 5)

  return {
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
  }
}
