/**
 * useElementPicker
 *
 * Focused, single-responsibility hook for the iframe inspector.
 * Responsibilities:
 *   1. Inject the inspector script when the iframe loads
 *   2. Surface the latest captured element as `lastCaptured`
 *   3. Send control messages back into the iframe (active slot label, pin count)
 *
 * NOT responsible for:
 *   - Managing the array of ticket changes (that's useTicketChanges)
 *   - Deciding which change slot receives the captured element (that's SiteEditPanel)
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import type { ElementContext, InspectorMessage } from './types'

export interface UseElementPickerReturn {
  /** Attach to the <iframe> element */
  iframeRef: React.RefObject<HTMLIFrameElement>

  /** Most recently captured element; null until user clicks something */
  lastCaptured: ElementContext | null

  /** Call after routing lastCaptured to a change slot to reset it */
  clearLastCaptured: () => void

  /**
   * Tell the iframe which change slot is currently active.
   * The inspector updates its banner to "Pinning for Change N".
   * Pass null to show the "select a change slot" prompt instead.
   */
  announceActiveSlot: (label: string | null) => void

  /**
   * Sync the pin count badge in the iframe.
   * @param pinned  How many slots already have an element
   * @param max     Hard cap (MAX_CHANGES)
   */
  announceSlotCount: (pinned: number, max: number) => void
}

export function useElementPicker(opts?: {
  /** Called when the user presses Esc inside the iframe */
  onCancel?: () => void
}): UseElementPickerReturn {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [lastCaptured, setLastCaptured] = useState<ElementContext | null>(null)

  // ── Inject inspector on iframe load ───────────────────────────────────────
  const handleIframeLoad = useCallback(() => {
    const iframe = iframeRef.current
    if (!iframe) return

    try {
      const doc = iframe.contentDocument
      if (!doc?.body) return

      import('./inspectorScript').then(({ buildInspectorScript }) => {
        const script = doc.createElement('script')
        script.textContent = buildInspectorScript()
        doc.body.appendChild(script)
      })
    } catch (err) {
      console.error('[ElementPicker] Could not inject inspector:', err)
    }
  }, [])

  useEffect(() => {
    const iframe = iframeRef.current
    if (!iframe) return
    iframe.addEventListener('load', handleIframeLoad)
    return () => iframe.removeEventListener('load', handleIframeLoad)
  }, [handleIframeLoad])

  // ── Listen for postMessages from the iframe ────────────────────────────────
  useEffect(() => {
    function handleMessage(event: MessageEvent) {
      const data = event.data as InspectorMessage | { type: string }
      if (!data?.type) return

      if (data.type === 'WEBMAGIC_ELEMENT_SELECTED') {
        setLastCaptured((data as InspectorMessage).payload)
      }

      if (data.type === 'WEBMAGIC_INSPECTOR_CANCELLED') {
        opts?.onCancel?.()
      }
    }

    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [opts?.onCancel])

  // ── Outbound control helpers ───────────────────────────────────────────────
  const postToIframe = useCallback((msg: object) => {
    try {
      iframeRef.current?.contentWindow?.postMessage(msg, '*')
    } catch {
      // Same-origin access guard — shouldn't happen for our own sites
    }
  }, [])

  const clearLastCaptured = useCallback(() => setLastCaptured(null), [])

  const announceActiveSlot = useCallback(
    (label: string | null) => postToIframe({ type: 'WEBMAGIC_ACTIVE_SLOT', label }),
    [postToIframe],
  )

  const announceSlotCount = useCallback(
    (pinned: number, max: number) =>
      postToIframe({ type: 'WEBMAGIC_PIN_COUNT', count: pinned, max }),
    [postToIframe],
  )

  return {
    iframeRef,
    lastCaptured,
    clearLastCaptured,
    announceActiveSlot,
    announceSlotCount,
  }
}
