/**
 * CreateTicketForm
 *
 * Customer-facing ticket creation form with optional visual element annotation.
 * When the ticket category is "site_edit", customers can open their live site
 * in an overlay, click an element to annotate it, and have that element's
 * context automatically attached to the ticket for the AI pipeline.
 */
import React, { useState, useEffect } from 'react'
import { api } from '../../services/api'
import { SiteSelector } from '../CustomerPortal'
import {
  ElementPickerOverlay,
  ElementPickerCard,
  useElementPicker,
} from '../ElementPicker'
import type { ElementContext } from '../ElementPicker'
import './CreateTicketForm.css'

// ── Types ─────────────────────────────────────────────────────────────────

interface Site {
  site_id: string
  slug: string
  site_title: string
  is_primary: boolean
  status?: string
  subscription_status?: string
}

interface FormData {
  subject: string
  description: string
  category: string
  site_id: string
}

interface CreateTicketFormProps {
  siteId?: string
  onSuccess?: (ticket: any) => void
  onCancel?: () => void
}

// ── Helpers ───────────────────────────────────────────────────────────────

/** Derive the public URL for a site slug (same origin, path-based routing). */
function resolveSiteUrl(slug: string): string {
  return `${window.location.origin}/${slug}/`
}

/** Only show the element picker when the category is "site_edit". */
function isSiteEditCategory(category: string): boolean {
  return category === 'site_edit'
}

// ── Component ─────────────────────────────────────────────────────────────

const CreateTicketForm: React.FC<CreateTicketFormProps> = ({
  siteId,
  onSuccess,
  onCancel,
}) => {
  const [categories, setCategories] = useState<any>(null)
  const [sites, setSites] = useState<Site[]>([])
  const [loadingSites, setLoadingSites] = useState(true)
  const [hasMultipleSites, setHasMultipleSites] = useState(false)
  const [formData, setFormData] = useState<FormData>({
    subject: '',
    description: '',
    category: 'question',
    site_id: siteId || '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [siteSelectionError, setSiteSelectionError] = useState<string | null>(null)

  // ── Element picker state ───────────────────────────────────────────────
  const { isOpen, selectedElement, openPicker, closePicker, clearSelection, iframeRef } =
    useElementPicker()

  // ── Data loading ───────────────────────────────────────────────────────

  useEffect(() => {
    loadCategories()
    loadCustomerSites()
  }, [])

  const loadCategories = async () => {
    try {
      const data = await api.getTicketCategories()
      setCategories(data)
    } catch (err) {
      console.error('Failed to load categories:', err)
    }
  }

  const loadCustomerSites = async () => {
    setLoadingSites(true)
    try {
      const response = await api.getMySites()
      setSites(response.sites || [])
      setHasMultipleSites(response.has_multiple_sites || false)

      if (response.sites && response.sites.length === 1) {
        setFormData(prev => ({ ...prev, site_id: response.sites[0].site_id }))
      } else if (!siteId && response.sites) {
        const primarySite = response.sites.find((s: Site) => s.is_primary)
        if (primarySite) {
          setFormData(prev => ({ ...prev, site_id: primarySite.site_id }))
        }
      }
    } catch (err) {
      console.error('Failed to load customer sites:', err)
    } finally {
      setLoadingSites(false)
    }
  }

  // ── Handlers ───────────────────────────────────────────────────────────

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
  ) => {
    setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleSiteSelect = (id: string) => {
    setFormData(prev => ({ ...prev, site_id: id }))
    setSiteSelectionError(null)
  }

  /** Find the slug for the currently-selected site (for iframe URL). */
  const getSelectedSiteSlug = (): string | null => {
    const site = sites.find(s => s.site_id === formData.site_id)
    return site?.slug ?? null
  }

  const handleOpenPicker = () => {
    const slug = getSelectedSiteSlug()
    if (!slug) return
    openPicker(resolveSiteUrl(slug))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSiteSelectionError(null)
    setLoading(true)

    if (hasMultipleSites && !formData.site_id) {
      setSiteSelectionError('Please select which website this ticket is for')
      setLoading(false)
      return
    }

    try {
      const ticket = await api.createTicket({
        ...formData,
        // Attach element context only for site_edit tickets that have a selection
        element_context:
          isSiteEditCategory(formData.category) && selectedElement
            ? (selectedElement as ElementContext)
            : null,
      })

      setFormData({
        subject: '',
        description: '',
        category: 'question',
        site_id: siteId || (sites.length === 1 ? sites[0].site_id : ''),
      })
      clearSelection()

      if (onSuccess) onSuccess(ticket)
    } catch (err: any) {
      const errorResponse = err.response?.data?.detail

      if (
        errorResponse &&
        typeof errorResponse === 'object' &&
        errorResponse.error === 'site_selection_required'
      ) {
        setSiteSelectionError(errorResponse.message)
        if (errorResponse.sites) {
          setSites(errorResponse.sites)
          setHasMultipleSites(true)
        }
      } else {
        setError(
          typeof errorResponse === 'string' ? errorResponse : 'Failed to create ticket',
        )
      }
    } finally {
      setLoading(false)
    }
  }

  // ── Derived state ──────────────────────────────────────────────────────

  const canPickElement =
    isSiteEditCategory(formData.category) && !!getSelectedSiteSlug()

  // ── Render ─────────────────────────────────────────────────────────────

  return (
    <>
      {/* Full-screen iframe overlay — mounted in a portal-like pattern outside the form */}
      {isOpen && (
        <ElementPickerOverlay
          siteUrl={`${window.location.origin}/${getSelectedSiteSlug()}/`}
          iframeRef={iframeRef}
          onClose={closePicker}
        />
      )}

      <div className="create-ticket-form">
        <form onSubmit={handleSubmit}>
          {/* ── Site selector (multi-site customers) ── */}
          {!siteId && hasMultipleSites && sites.length > 0 && (
            <SiteSelector
              sites={sites}
              selectedSiteId={formData.site_id}
              onSelect={handleSiteSelect}
              label="Which website is this ticket for?"
              required
              disabled={loading || loadingSites}
              showStatus
              error={siteSelectionError || undefined}
            />
          )}

          {loadingSites && !siteId && (
            <div className="form-info">
              <span className="spinner-small" />
              <span>Loading your websites…</span>
            </div>
          )}

          {/* ── Category ── */}
          <div className="form-group">
            <label htmlFor="category">Category *</label>
            <select
              id="category"
              name="category"
              value={formData.category}
              onChange={handleChange}
              required
              disabled={loading}
            >
              {categories?.categories?.map((cat: string) => (
                <option key={cat} value={cat}>
                  {cat.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </option>
              ))}
            </select>
            {categories?.descriptions && (
              <p className="form-help">{categories.descriptions[formData.category]}</p>
            )}
          </div>

          {/* ── Subject ── */}
          <div className="form-group">
            <label htmlFor="subject">Subject *</label>
            <input
              type="text"
              id="subject"
              name="subject"
              value={formData.subject}
              onChange={handleChange}
              placeholder="Brief summary of your request"
              required
              minLength={5}
              maxLength={255}
              disabled={loading}
            />
          </div>

          {/* ── Description ── */}
          <div className="form-group">
            <label htmlFor="description">Description *</label>
            <textarea
              id="description"
              name="description"
              value={formData.description}
              onChange={handleChange}
              placeholder="Please describe what you'd like changed or what issue you're experiencing…"
              required
              minLength={10}
              rows={6}
              disabled={loading}
            />
            <p className="form-help">
              Be as specific as possible — the more detail you provide, the faster we can help.
            </p>
          </div>

          {/* ── Element picker (site_edit only) ── */}
          {canPickElement && (
            <div className="form-group">
              <label>Pin a specific element <span className="form-label-optional">(optional)</span></label>

              {selectedElement ? (
                <ElementPickerCard element={selectedElement} onRemove={clearSelection} />
              ) : (
                <div className="element-picker-trigger">
                  <button
                    type="button"
                    className="btn btn-picker"
                    onClick={handleOpenPicker}
                    disabled={loading}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="11" cy="11" r="8" />
                      <path d="M21 21l-4.35-4.35" />
                      <line x1="11" y1="8" x2="11" y2="14" />
                      <line x1="8" y1="11" x2="14" y2="11" />
                    </svg>
                    Open my site and select element
                  </button>
                  <p className="form-help">
                    Click to open your website — then click any element (heading, button, section…)
                    to pin it here so our team knows exactly what to update.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* ── Error ── */}
          {error && (
            <div className="form-error">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          {/* ── Actions ── */}
          <div className="form-actions">
            {onCancel && (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={onCancel}
                disabled={loading}
              >
                Cancel
              </button>
            )}
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? (
                <>
                  <span className="spinner" />
                  <span>Creating…</span>
                </>
              ) : (
                'Create Ticket'
              )}
            </button>
          </div>
        </form>
      </div>
    </>
  )
}

export default CreateTicketForm
