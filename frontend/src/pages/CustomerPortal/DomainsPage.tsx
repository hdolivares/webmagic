/**
 * Customer Domains Page
 * 
 * Page for customers to manage their custom domain
 */
import React, { useState, useEffect } from 'react'
import { api } from '../../services/api'
import { DomainSetup, DomainManagement } from '../../components/Domains'
import './DomainsPage.css'

const DomainsPage: React.FC = () => {
  const [site, setSite] = useState<any>(null)
  const [domainStatus, setDomainStatus] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadSiteAndDomain()
  }, [])

  const loadSiteAndDomain = async () => {
    setLoading(true)
    setError(null)

    try {
      // Get customer's site from token or API
      const customerEmail = localStorage.getItem('customer_email')
      // In a real implementation, you'd have an endpoint to get customer's site
      // For now, we'll need to store the site_id when customer logs in
      const siteId = localStorage.getItem('customer_site_id')

      if (!siteId) {
        setError('No site found for your account. Please contact support.')
        setLoading(false)
        return
      }

      // Load domain status
      try {
        const status = await api.getDomainStatus(siteId)
        setDomainStatus(status)
      } catch (err: any) {
        // If no domain exists yet, that's okay
        if (err.response?.status !== 404) {
          console.error('Failed to load domain status:', err)
        }
      }

      setSite({ id: siteId })
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load site information')
    } finally {
      setLoading(false)
    }
  }

  const handleDomainUpdate = () => {
    loadSiteAndDomain()
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

      {hasDomain ? (
        <DomainManagement
          siteId={site.id}
          onUpdate={handleDomainUpdate}
        />
      ) : (
        <DomainSetup
          siteId={site.id}
          onComplete={handleDomainUpdate}
        />
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

