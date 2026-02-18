/**
 * useElementPicker — state management hook for the visual element picker.
 *
 * Encapsulates all picker lifecycle:
 *   • open / close the overlay
 *   • listen for postMessage from the iframe
 *   • store / clear the captured ElementContext
 *
 * The component layer stays declarative; all side-effects live here.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import type { ElementContext, InspectorMessage } from './types'

export interface UseElementPickerReturn {
  /** Whether the iframe overlay is currently visible */
  isOpen: boolean

  /** The most recently captured element, or null if none yet */
  selectedElement: ElementContext | null

  /** Open the picker overlay for a given site URL */
  openPicker: (siteUrl: string) => void

  /** Close the overlay without keeping a selection */
  closePicker: () => void

  /** Clear the captured element (user removed the annotation) */
  clearSelection: () => void

  /** Ref to attach to the <iframe> so we can inject the script on load */
  iframeRef: React.RefObject<HTMLIFrameElement>
}

export function useElementPicker(): UseElementPickerReturn {
  const [isOpen, setIsOpen] = useState(false)
  const [siteUrl, setSiteUrl] = useState<string | null>(null)
  const [selectedElement, setSelectedElement] = useState<ElementContext | null>(null)
  const iframeRef = useRef<HTMLIFrameElement>(null)

  // ── Inject the inspector script once the iframe finishes loading ──────────
  const handleIframeLoad = useCallback(() => {
    const iframe = iframeRef.current
    if (!iframe) return

    try {
      const doc = iframe.contentDocument
      if (!doc) return

      // Dynamically import the script builder to keep the main bundle lean
      import('./inspectorScript').then(({ buildInspectorScript }) => {
        const script = doc.createElement('script')
        script.textContent = buildInspectorScript()
        doc.body.appendChild(script)
      })
    } catch (err) {
      // Same-origin access denied (shouldn't happen for our own sites)
      console.error('[ElementPicker] Could not inject inspector script:', err)
    }
  }, [])

  // ── Listen for postMessage from the iframe ────────────────────────────────
  useEffect(() => {
    if (!isOpen) return

    function handleMessage(event: MessageEvent) {
      const data = event.data as InspectorMessage | { type: string }
      if (!data || !data.type) return

      if (data.type === 'WEBMAGIC_ELEMENT_SELECTED') {
        setSelectedElement((data as InspectorMessage).payload)
        setIsOpen(false)
      }

      if (data.type === 'WEBMAGIC_INSPECTOR_CANCELLED') {
        setIsOpen(false)
      }
    }

    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [isOpen])

  // ── Attach iframe load listener whenever the overlay opens ────────────────
  useEffect(() => {
    const iframe = iframeRef.current
    if (!iframe || !isOpen) return

    iframe.addEventListener('load', handleIframeLoad)
    return () => iframe.removeEventListener('load', handleIframeLoad)
  }, [isOpen, handleIframeLoad])

  // ── Public API ─────────────────────────────────────────────────────────────
  const openPicker = useCallback((url: string) => {
    setSiteUrl(url)
    setIsOpen(true)
  }, [])

  const closePicker = useCallback(() => {
    setIsOpen(false)
  }, [])

  const clearSelection = useCallback(() => {
    setSelectedElement(null)
  }, [])

  return {
    isOpen,
    selectedElement,
    openPicker,
    closePicker,
    clearSelection,
    iframeRef,
  }
}
