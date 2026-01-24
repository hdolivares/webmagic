/**
 * Create Ticket Form Component
 * 
 * Form for customers to create new support tickets.
 * Supports multi-site selection for customers with multiple websites.
 * 
 * Updated: January 24, 2026 - Added multi-site support
 */
import React, { useState, useEffect } from 'react'
import { api } from '../../services/api'
import { SiteSelector } from '../CustomerPortal'
import './CreateTicketForm.css'

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

const CreateTicketForm: React.FC<CreateTicketFormProps> = ({
  siteId,
  onSuccess,
  onCancel
}) => {
  const [categories, setCategories] = useState<any>(null)
  const [sites, setSites] = useState<Site[]>([])
  const [loadingSites, setLoadingSites] = useState(true)
  const [hasMultipleSites, setHasMultipleSites] = useState(false)
  const [formData, setFormData] = useState({
    subject: '',
    description: '',
    category: 'question',
    site_id: siteId || ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [siteSelectionError, setSiteSelectionError] = useState<string | null>(null)

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
      
      // Auto-select site if only one or if primary site
      if (response.sites && response.sites.length === 1) {
        setFormData(prev => ({ ...prev, site_id: response.sites[0].site_id }))
      } else if (!siteId && response.sites) {
        // Pre-select primary site if customer has multiple
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

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  const handleSiteSelect = (siteId: string) => {
    setFormData({
      ...formData,
      site_id: siteId
    })
    setSiteSelectionError(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSiteSelectionError(null)
    setLoading(true)

    // Validate site selection for multi-site customers
    if (hasMultipleSites && !formData.site_id) {
      setSiteSelectionError('Please select which website this ticket is for')
      setLoading(false)
      return
    }

    try {
      const ticket = await api.createTicket(formData)
      
      // Reset form
      setFormData({
        subject: '',
        description: '',
        category: 'question',
        site_id: siteId || (sites.length === 1 ? sites[0].site_id : '')
      })

      if (onSuccess) {
        onSuccess(ticket)
      }
    } catch (err: any) {
      const errorResponse = err.response?.data?.detail
      
      // Handle multi-site error response from API
      if (errorResponse && typeof errorResponse === 'object' && errorResponse.error === 'site_selection_required') {
        setSiteSelectionError(errorResponse.message)
        if (errorResponse.sites) {
          setSites(errorResponse.sites)
          setHasMultipleSites(true)
        }
      } else {
        setError(typeof errorResponse === 'string' ? errorResponse : 'Failed to create ticket')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="create-ticket-form">
      <form onSubmit={handleSubmit}>
        {/* Site Selection (for multi-site customers) */}
        {!siteId && hasMultipleSites && sites.length > 0 && (
          <SiteSelector
            sites={sites}
            selectedSiteId={formData.site_id}
            onSelect={handleSiteSelect}
            label="Which website is this ticket for?"
            required={true}
            disabled={loading || loadingSites}
            showStatus={true}
            error={siteSelectionError || undefined}
          />
        )}
        
        {/* Loading sites indicator */}
        {loadingSites && !siteId && (
          <div className="form-info">
            <span className="spinner-small"></span>
            <span>Loading your websites...</span>
          </div>
        )}
        
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
            <p className="form-help">
              {categories.descriptions[formData.category]}
            </p>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="subject">Subject *</label>
          <input
            type="text"
            id="subject"
            name="subject"
            value={formData.subject}
            onChange={handleChange}
            placeholder="Brief summary of your issue"
            required
            minLength={5}
            maxLength={255}
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="description">Description *</label>
          <textarea
            id="description"
            name="description"
            value={formData.description}
            onChange={handleChange}
            placeholder="Please provide detailed information about your issue or question..."
            required
            minLength={10}
            rows={6}
            disabled={loading}
          />
          <p className="form-help">
            Please be as detailed as possible to help us assist you better.
          </p>
        </div>

        {error && (
          <div className="form-error">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <span>{error}</span>
          </div>
        )}

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
          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                <span>Creating...</span>
              </>
            ) : (
              'Create Ticket'
            )}
          </button>
        </div>
      </form>
    </div>
  )
}

export default CreateTicketForm

