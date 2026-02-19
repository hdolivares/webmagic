/**
 * Customer Domains Page
 *
 * Page for customers to manage their custom domain.
 * Loads site list via the customer API (same as MySitesPage) so customers
 * with multiple sites can select which one they want to manage.
 */
import React, { useState, useEffect } from 'react'
import { api } from '../../services/api'
import { DomainSetup, DomainManagement } from '../../components/Domains'
import './DomainsPage.css'

interface CustomerSite {
  site_id: string
  slug: string
  site_title: string
  is_primary: boolean
}

const DomainsPage: React.FC = () => {
  const [sites, setSites] = useState<CustomerSite[]>([])
  const [selectedSiteId, setSelectedSiteId] = useState<string | null>(null)
  const [domainStatus, setDomainStatus] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadSites()
  }, [])

  // Reload domain status whenever the selected site changes
  useEffect(() => {
    if (selectedSiteId) {
      loadDomainStatus(selectedSiteId)
    }
  }, [selectedSiteId])

  const loadSites = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await api.getMySites()
      const fetchedSites: CustomerSite[] = response.sites ?? []

      if (fetchedSites.length === 0) {
        setError('No site found for your account. Please contact support.')
        setLoading(false)
        return
      }

      setSites(fetchedSites)

      // Default to the primary site, fall back to first
      const primary = fetchedSites.find((s) => s.is_primary) ?? fetchedSites[0]
      setSelectedSiteId(primary.site_id)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load site information')
      setLoading(false)
    }
  }

  const loadDomainStatus = async (siteId: string) => {
    setLoading(true)
    setDomainStatus(null)

    try {
      const status = await api.getDomainStatus(siteId)
      setDomainStatus(status)
    } catch (err: any) {
      // 404 means no domain connected yet — that's fine
      if (err.response?.status !== 404) {
        console.error('Failed to load domain status:', err)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleDomainUpdate = () => {
    if (selectedSiteId) {
      loadDomainStatus(selectedSiteId)
    }
  }

  if (loading) {
    return (
      <div className="domains-page">
        <div className="loading-state">
          <div className="spinner-large"></div>
          <p>Loading...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="domains-page">
        <div className="error-state">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <h2>Unable to Load Site</h2>
          <p>{error}</p>
        </div>
      </div>
    )
  }

  const hasDomain = domainStatus && domainStatus.domain

  return (
    <div className="domains-page">
      <div className="domains-page-header">
        <h1>Custom Domain</h1>
        <p className="page-description">
          Connect your own domain to your website for a professional presence
        </p>
      </div>

      {/* Site selector — only shown when the customer owns more than one site */}
      {sites.length > 1 && (
        <div className="domains-site-selector">
          <label htmlFor="domain-site-select">Managing domain for:</label>
          <select
            id="domain-site-select"
            value={selectedSiteId ?? ''}
            onChange={(e) => setSelectedSiteId(e.target.value)}
          >
            {sites.map((s) => (
              <option key={s.site_id} value={s.site_id}>
                {s.site_title || s.slug}{s.is_primary ? ' (primary)' : ''}
              </option>
            ))}
          </select>
        </div>
      )}

      {selectedSiteId && (
        hasDomain ? (
          <DomainManagement
            siteId={selectedSiteId}
            onDisconnected={handleDomainUpdate}
          />
        ) : (
          <DomainSetup siteId={selectedSiteId} onComplete={handleDomainUpdate} />
        )
      )}

      <div className="domains-help">
        <h3>Need Help?</h3>
        <p>
          If you're having trouble connecting your domain, our support team is here to help.{' '}
          <a href="/customer/tickets">Create a support ticket</a> and we'll assist you.
        </p>
      </div>
    </div>
  )
}

export default DomainsPage

