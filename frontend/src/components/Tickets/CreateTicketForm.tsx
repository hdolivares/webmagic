/**
 * CreateTicketForm
 *
 * Standard ticket creation for all categories EXCEPT site_edit.
 * When the customer picks "site_edit", the form is replaced by SiteEditPanel —
 * a full-screen split-pane that lets them browse their live site, pin elements,
 * and type their request simultaneously.
 *
 * URL resolution:
 *   Customer sites are served at {origin}/{slug}/ (same origin as the portal),
 *   so the iframe has full same-origin DOM access for the element inspector.
 */
import React, { useState, useEffect } from 'react'
import { api } from '../../services/api'
import { SiteSelector } from '../CustomerPortal'
import { SiteEditPanel } from './SiteEditPanel'
import type { SiteEditSubmitData } from './SiteEditPanel'
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

interface CreateTicketFormProps {
  siteId?: string
  onSuccess?: (ticket: any) => void
  onCancel?: () => void
}

// ── Helpers ───────────────────────────────────────────────────────────────

/** Returns the publicly-accessible URL for a site slug. */
function resolveSiteUrl(slug: string): string {
  return `${window.location.origin}/${slug}/`
}

const CATEGORY_LABELS: Record<string, string> = {
  billing: 'Billing',
  technical_support: 'Technical Support',
  site_edit: 'Site Edit',
  question: 'Question',
  other: 'Other',
}

const CATEGORY_DESCRIPTIONS: Record<string, string> = {
  billing: 'Questions about payments, subscriptions, invoices, or billing issues',
  technical_support: 'Technical problems with your website or platform features',
  site_edit: 'Requests for changes or updates to your website',
  question: 'General questions about features, how-to guides, or information',
  other: 'Any other topic not covered by the above categories',
}

// ── Component ─────────────────────────────────────────────────────────────

const CreateTicketForm: React.FC<CreateTicketFormProps> = ({ siteId, onSuccess, onCancel }) => {
  const [sites, setSites] = useState<Site[]>([])
  const [loadingSites, setLoadingSites] = useState(true)
  const [hasMultipleSites, setHasMultipleSites] = useState(false)

  const [category, setCategory] = useState('question')
  const [subject, setSubject] = useState('')
  const [description, setDescription] = useState('')
  const [selectedSiteId, setSelectedSiteId] = useState(siteId || '')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [siteSelectionError, setSiteSelectionError] = useState<string | null>(null)

  /** True when the site_edit panel is open */
  const [siteEditOpen, setSiteEditOpen] = useState(false)

  // ── Data loading ───────────────────────────────────────────────────────

  useEffect(() => {
    loadCustomerSites()
  }, [])

  const loadCustomerSites = async () => {
    setLoadingSites(true)
    try {
      const response = await api.getMySites()
      const siteList: Site[] = response.sites || []
      setSites(siteList)
      setHasMultipleSites(response.has_multiple_sites || false)

      // Auto-select the only site or the primary site
      if (!siteId) {
        if (siteList.length === 1) {
          setSelectedSiteId(siteList[0].site_id)
        } else {
          const primary = siteList.find(s => s.is_primary)
          if (primary) setSelectedSiteId(primary.site_id)
        }
      }
    } catch (err) {
      console.error('Failed to load sites:', err)
    } finally {
      setLoadingSites(false)
    }
  }

  // ── Derived values ─────────────────────────────────────────────────────

  const selectedSite = sites.find(s => s.site_id === selectedSiteId) ?? null
  const isSiteEdit = category === 'site_edit'
  const canOpenSiteEdit = isSiteEdit && !!selectedSite

  // ── Standard submission (all non-site_edit categories) ────────────────

  const handleStandardSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSiteSelectionError(null)

    if (hasMultipleSites && !selectedSiteId) {
      setSiteSelectionError('Please select which website this ticket is for.')
      return
    }

    setLoading(true)
    try {
      const ticket = await api.createTicket({
        subject,
        description,
        category,
        site_id: selectedSiteId || undefined,
        element_context: null,
      })
      resetForm()
      onSuccess?.(ticket)
    } catch (err: any) {
      const detail = err.response?.data?.detail
      if (detail?.error === 'site_selection_required') {
        setSiteSelectionError(detail.message)
        if (detail.sites) { setSites(detail.sites); setHasMultipleSites(true) }
      } else {
        setError(typeof detail === 'string' ? detail : 'Failed to create ticket.')
      }
    } finally {
      setLoading(false)
    }
  }

  // ── Site-edit panel submission ─────────────────────────────────────────

  const handleSiteEditSubmit = async (data: SiteEditSubmitData) => {
    const ticket = await api.createTicket({
      subject: data.subject,
      description: data.description,
      category: 'site_edit',
      site_id: selectedSiteId || undefined,
      element_context: data.element_context,
    })
    setSiteEditOpen(false)
    onSuccess?.(ticket)
  }

  const resetForm = () => {
    setSubject('')
    setDescription('')
    setCategory('question')
    if (!siteId) setSelectedSiteId(sites.length === 1 ? sites[0].site_id : '')
  }

  // ── Render: Site Edit Panel (full-screen) ──────────────────────────────

  if (siteEditOpen && selectedSite) {
    return (
      <SiteEditPanel
        siteUrl={resolveSiteUrl(selectedSite.slug)}
        siteName={selectedSite.site_title || selectedSite.slug}
        onSubmit={handleSiteEditSubmit}
        onClose={() => setSiteEditOpen(false)}
      />
    )
  }

  // ── Render: Standard form ─────────────────────────────────────────────

  return (
    <div className="create-ticket-form">
      <form onSubmit={handleStandardSubmit}>

        {/* Site selector (multi-site customers) */}
        {!siteId && hasMultipleSites && sites.length > 0 && (
          <SiteSelector
            sites={sites}
            selectedSiteId={selectedSiteId}
            onSelect={id => { setSelectedSiteId(id); setSiteSelectionError(null) }}
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

        {/* Category */}
        <div className="form-group">
          <label htmlFor="category">Category *</label>
          <select
            id="category"
            value={category}
            onChange={e => setCategory(e.target.value)}
            required
            disabled={loading}
          >
            {Object.entries(CATEGORY_LABELS).map(([val, label]) => (
              <option key={val} value={val}>{label}</option>
            ))}
          </select>
          <p className="form-help">{CATEGORY_DESCRIPTIONS[category]}</p>
        </div>

        {/* Site Edit CTA — replaces the standard form fields */}
        {isSiteEdit ? (
          <div className="form-group">
            {canOpenSiteEdit ? (
              <div className="element-picker-trigger">
                <button
                  type="button"
                  className="btn btn-picker"
                  onClick={() => setSiteEditOpen(true)}
                  disabled={loading || loadingSites}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                  </svg>
                  Open "{selectedSite?.site_title || selectedSite?.slug}" and describe changes
                </button>
                <p className="form-help">
                  Your site opens alongside this form — click any element to pin it,
                  then describe what you'd like changed. Up to 3 elements per request.
                </p>
              </div>
            ) : (
              <p className="form-help" style={{ color: 'var(--error-color, #ef4444)' }}>
                Please select a website above before opening the site editor.
              </p>
            )}
          </div>
        ) : (
          <>
            {/* Subject */}
            <div className="form-group">
              <label htmlFor="subject">Subject *</label>
              <input
                type="text"
                id="subject"
                value={subject}
                onChange={e => setSubject(e.target.value)}
                placeholder="Brief summary of your issue"
                required
                minLength={5}
                maxLength={255}
                disabled={loading}
              />
            </div>

            {/* Description */}
            <div className="form-group">
              <label htmlFor="description">Description *</label>
              <textarea
                id="description"
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="Please provide detailed information about your issue or question…"
                required
                minLength={10}
                rows={6}
                disabled={loading}
              />
              <p className="form-help">
                Be as detailed as possible to help us assist you better.
              </p>
            </div>
          </>
        )}

        {/* Error */}
        {error && (
          <div className="form-error">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <span>{error}</span>
          </div>
        )}

        {/* Actions — hidden for site_edit (the panel has its own) */}
        {!isSiteEdit && (
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
                <><span className="spinner" /><span>Creating…</span></>
              ) : 'Create Ticket'}
            </button>
          </div>
        )}
      </form>
    </div>
  )
}

export default CreateTicketForm
