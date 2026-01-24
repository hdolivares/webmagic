/**
 * My Sites Page - Customer Portal
 * 
 * Displays all websites owned by the customer with management options.
 * Supports single and multi-site customers.
 * 
 * Author: WebMagic Team
 * Date: January 24, 2026
 */
import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../services/api'
import './MySitesPage.css'

interface Site {
  site_id: string
  slug: string
  site_title: string
  site_url: string
  status: string
  subscription_status: string
  is_primary: boolean
  acquired_at: string
  next_billing_date?: string
  custom_domain?: string
  purchase_amount?: number
  monthly_amount?: number
}

interface MySitesData {
  sites: Site[]
  total: number
  has_multiple_sites: boolean
}

const MySitesPage: React.FC = () => {
  const navigate = useNavigate()
  const [data, setData] = useState<MySitesData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadSites()
  }, [])

  const loadSites = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await api.getMySites()
      setData(response)
    } catch (err: any) {
      console.error('Failed to load sites:', err)
      setError(err.response?.data?.detail || 'Failed to load your sites')
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadgeClass = (status: string): string => {
    const statusMap: Record<string, string> = {
      preview: 'status-preview',
      owned: 'status-owned',
      active: 'status-active',
      suspended: 'status-suspended',
      cancelled: 'status-cancelled'
    }
    return statusMap[status] || 'status-default'
  }

  const getSubscriptionBadgeClass = (status: string): string => {
    const statusMap: Record<string, string> = {
      active: 'subscription-active',
      past_due: 'subscription-past-due',
      cancelled: 'subscription-cancelled',
      paused: 'subscription-paused'
    }
    return statusMap[status] || 'subscription-default'
  }

  const formatStatus = (status: string): string => {
    return status
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  const formatDate = (dateString?: string): string => {
    if (!dateString) return 'N/A'
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  if (loading) {
    return (
      <div className="my-sites-page">
        <div className="page-header">
          <h1>My Websites</h1>
        </div>
        <div className="loading-state">
          <div className="spinner-large"></div>
          <p>Loading your websites...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="my-sites-page">
        <div className="page-header">
          <h1>My Websites</h1>
        </div>
        <div className="error-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <p>{error}</p>
          <button className="btn btn-secondary" onClick={loadSites}>
            Try Again
          </button>
        </div>
      </div>
    )
  }

  if (!data || data.sites.length === 0) {
    return (
      <div className="my-sites-page">
        <div className="page-header">
          <h1>My Websites</h1>
        </div>
        <div className="empty-state">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
            <line x1="9" y1="3" x2="9" y2="21"/>
          </svg>
          <h2>No Websites Yet</h2>
          <p>You haven't purchased any websites yet.</p>
          <button
            className="btn btn-primary"
            onClick={() => window.location.href = 'https://web.lavish.solutions'}
          >
            Browse Available Sites
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="my-sites-page">
      <div className="page-header">
        <div>
          <h1>My Websites</h1>
          <p className="page-description">
            {data.has_multiple_sites
              ? `You own ${data.total} websites`
              : 'Manage your website'}
          </p>
        </div>
      </div>

      <div className="sites-grid">
        {data.sites.map((site) => (
          <div
            key={site.site_id}
            className="site-card"
            onClick={() => navigate(`/customer/site/${site.site_id}`)}
          >
            {/* Header */}
            <div className="site-card-header">
              <div className="site-title-row">
                <h3 className="site-title">
                  {site.site_title || site.slug}
                </h3>
                {site.is_primary && (
                  <span className="badge badge-primary">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                    </svg>
                    Primary
                  </span>
                )}
              </div>
              
              {/* Site URL */}
              <a
                href={site.site_url}
                target="_blank"
                rel="noopener noreferrer"
                className="site-url"
                onClick={(e) => e.stopPropagation()}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                  <polyline points="15 3 21 3 21 9"/>
                  <line x1="10" y1="14" x2="21" y2="3"/>
                </svg>
                {site.custom_domain || `sites.lavish.solutions/${site.slug}`}
              </a>
            </div>

            {/* Status Badges */}
            <div className="site-card-status">
              <span className={`status-badge ${getStatusBadgeClass(site.status)}`}>
                {formatStatus(site.status)}
              </span>
              {site.subscription_status && (
                <span className={`status-badge ${getSubscriptionBadgeClass(site.subscription_status)}`}>
                  {formatStatus(site.subscription_status)}
                </span>
              )}
            </div>

            {/* Billing Info */}
            <div className="site-card-billing">
              <div className="billing-row">
                <span className="billing-label">Acquired</span>
                <span className="billing-value">{formatDate(site.acquired_at)}</span>
              </div>
              {site.next_billing_date && (
                <div className="billing-row">
                  <span className="billing-label">Next Billing</span>
                  <span className="billing-value">{formatDate(site.next_billing_date)}</span>
                </div>
              )}
              {site.monthly_amount && (
                <div className="billing-row">
                  <span className="billing-label">Monthly</span>
                  <span className="billing-value">${site.monthly_amount}</span>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="site-card-actions">
              <button
                className="btn btn-sm btn-primary"
                onClick={(e) => {
                  e.stopPropagation()
                  navigate(`/customer/tickets/new?site=${site.site_id}`)
                }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
                Create Ticket
              </button>
              <button
                className="btn btn-sm btn-secondary"
                onClick={(e) => {
                  e.stopPropagation()
                  window.open(site.site_url, '_blank')
                }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                  <polyline points="15 3 21 3 21 9"/>
                  <line x1="10" y1="14" x2="21" y2="3"/>
                </svg>
                View Site
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Multi-site info banner */}
      {data.has_multiple_sites && (
        <div className="multi-site-banner">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 16v-4"/>
            <path d="M12 8h.01"/>
          </svg>
          <div>
            <p className="banner-title">Managing Multiple Websites</p>
            <p className="banner-text">
              When creating support tickets, you'll be able to select which website the ticket is for.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

export default MySitesPage
