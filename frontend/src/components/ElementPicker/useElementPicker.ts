/**
 * useElementPicker — multi-element selection hook.
 *
 * Manages the full lifecycle of the visual element picker:
 *   • Stores up to MAX_SELECTIONS pinned elements
 *   • Injects the inspector script once the iframe loads
 *   • Syncs the current pin count back into the iframe so its badge stays current
 *   • Exposes stable siteUrl so the overlay always renders with the correct URL
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import type { ElementContext, InspectorMessage } from './types'

/** Hard cap on elements per ticket. Keeps LLM scope tight. */
export const MAX_SELECTIONS = 3

export interface UseElementPickerReturn {
  /** Whether the iframe panel is currently visible */
  isOpen: boolean

  /** The URL currently loaded in the iframe (null when picker is closed) */
  siteUrl: string | null

  /** Ordered list of pinned elements (max MAX_SELECTIONS) */
  selectedElements: ElementContext[]

  /** True when selectedElements.length < MAX_SELECTIONS */
  canAddMore: boolean

  /** Open the picker panel for a given site URL */
  openPicker: (url: string) => void

  /** Close the panel (does not clear selections) */
  closePicker: () => void

  /** Remove a pinned element by index */
  removeElement: (index: number) => void

  /** Clear all pinned elements */
  clearAll: () => void

  /** Ref to attach to the <iframe> element */
  iframeRef: React.RefObject<HTMLIFrameElement>
}

export function useElementPicker(): UseElementPickerReturn {
  const [isOpen, setIsOpen] = useState(false)
  const [siteUrl, setSiteUrl] = useState<string | null>(null)
  const [selectedElements, setSelectedElements] = useState<ElementContext[]>([])
  const iframeRef = useRef<HTMLIFrameElement>(null)

  const canAddMore = selectedElements.length < MAX_SELECTIONS

  // ── Inject inspector script when iframe loads ─────────────────────────────
  const handleIframeLoad = useCallback(() => {
    const iframe = iframeRef.current
    if (!iframe) return

    try {
      const doc = iframe.contentDocument
      if (!doc || !doc.body) return

      import('./inspectorScript').then(({ buildInspectorScript }) => {
        const script = doc.createElement('script')
        script.textContent = buildInspectorScript()
        doc.body.appendChild(script)
      })
    } catch (err) {
      console.error('[ElementPicker] Could not inject inspector script:', err)
    }
  }, [])

  // ── Sync pin count into the iframe whenever it changes ───────────────────
  const syncCountToIframe = useCallback(
    (elements: ElementContext[]) => {
      const iframe = iframeRef.current
      if (!iframe || !isOpen) return
      try {
        iframe.contentWindow?.postMessage(
          {
            type: 'WEBMAGIC_PIN_COUNT',
            count: elements.length,
            max: MAX_SELECTIONS,
          },
          '*',
        )
      } catch {
        // Cross-origin guard; shouldn't happen for same-origin sites
      }
    },
    [isOpen],
  )

  useEffect(() => {
    if (isOpen) syncCountToIframe(selectedElements)
  }, [selectedElements, isOpen, syncCountToIframe])

  // ── Listen for postMessage from the iframe ────────────────────────────────
  useEffect(() => {
    if (!isOpen) return

    function handleMessage(event: MessageEvent) {
      const data = event.data as InspectorMessage | { type: string }
      if (!data?.type) return

      if (data.type === 'WEBMAGIC_ELEMENT_SELECTED') {
        const incoming = (data as InspectorMessage).payload
        setSelectedElements(prev => {
          if (prev.length >= MAX_SELECTIONS) return prev
          const updated = [...prev, incoming]
          // Sync count immediately (state closure)
          setTimeout(() => syncCountToIframe(updated), 0)
          return updated
        })
        // Do NOT close — user continues selecting
      }

      if (data.type === 'WEBMAGIC_INSPECTOR_CANCELLED') {
        setIsOpen(false)
      }
    }

    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [isOpen, syncCountToIframe])

  // ── Attach iframe load listener whenever picker opens ─────────────────────
  useEffect(() => {
    const iframe = iframeRef.current
    if (!iframe || !isOpen) return

    iframe.addEventListener('load', handleIframeLoad)
    return () => iframe.removeEventListener('load', handleIframeLoad)
  }, [isOpen, handleIframeLoad])

  // ── Public API ────────────────────────────────────────────────────────────
  const openPicker = useCallback((url: string) => {
    setSiteUrl(url)
    setIsOpen(true)
  }, [])

  const closePicker = useCallback(() => {
    setIsOpen(false)
  }, [])

  const removeElement = useCallback((index: number) => {
    setSelectedElements(prev => prev.filter((_, i) => i !== index))
  }, [])

  const clearAll = useCallback(() => {
    setSelectedElements([])
  }, [])

  return {
    isOpen,
    siteUrl,
    selectedElements,
    canAddMore,
    openPicker,
    closePicker,
    removeElement,
    clearAll,
    iframeRef,
  }
}
