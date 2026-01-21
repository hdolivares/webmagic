/**
 * DomainManagement Component
 * 
 * Dashboard for managing connected custom domain.
 * Shows status, SSL info, and allows disconnection.
 * 
 * Author: WebMagic Team
 * Date: January 21, 2026
 */
import { useState, useEffect } from 'react'
import { api } from '@/services/api'
import './DomainManagement.css'

interface DomainManagementProps {
  siteId: string
  onAddDomain?: () => void
}

interface DomainStatus {
  id: string
  domain: string
  verification_status: string
  verified: boolean
  verified_at: string | null
  ssl_status: string | null
  ssl_expires: string | null
  last_checked: string | null
  verification_attempts: number
  dns_records: any
}

export function DomainManagement({ siteId, onAddDomain }: DomainManagementProps) {
  const [domainStatus, setDomainStatus] = useState<DomainStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isRemoving, setIsRemoving] = useState(false)
  const [showRemoveConfirm, setShowRemoveConfirm] = useState(false)

  useEffect(() => {
    fetchDomainStatus()
  }, [siteId])

  const fetchDomainStatus = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const status = await api.getDomainStatus(siteId)
      setDomainStatus(status)
    } catch (err: any) {
      console.error('Failed to fetch domain status:', err)
      if (err.response?.status !== 404) {
        setError('Failed to load domain status')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleRemoveDomain = async () => {
    setIsRemoving(true)
    setError(null)

    try {
      await api.disconnectDomain(siteId)
      setDomainStatus(null)
      setShowRemoveConfirm(false)
    } catch (err: any) {
      console.error('Failed to remove domain:', err)
      setError(err.response?.data?.detail || 'Failed to remove domain. Please try again.')
    } finally {
      setIsRemoving(false)
    }
  }

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'verified':
        return 'status-success'
      case 'pending':
        return 'status-warning'
      case 'failed':
        return 'status-error'
      default:
        return 'status-default'
    }
  }

  const getSSLStatusColor = (status: string | null): string => {
    if (!status) return 'status-default'
    switch (status) {
      case 'active':
        return 'status-success'
      case 'provisioning':
        return 'status-warning'
      case 'failed':
        return 'status-error'
      default:
        return 'status-default'
    }
  }

  const formatDate = (dateString: string | null): string => {
    if (!dateString) return 'Never'
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (isLoading) {
    return (
      <div className="domain-management">
        <div className="loading-skeleton">
          <div className="skeleton-header" />
          <div className="skeleton-content" />
          <div className="skeleton-content" />
        </div>
      </div>
    )
  }

  if (!domainStatus) {
    return (
      <div className="domain-management">
        <div className="empty-state">
          <svg className="empty-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
          </svg>
          <h3>No Custom Domain</h3>
          <p>Connect your own domain to give your site a professional web address.</p>
          
          <button className="btn-primary" onClick={onAddDomain}>
            <svg className="btn-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Connect Custom Domain
          </button>

          <div className="benefits-list">
            <div className="benefit-item">
              <svg className="benefit-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>Professional branding</span>
            </div>
            <div className="benefit-item">
              <svg className="benefit-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>Better SEO performance</span>
            </div>
            <div className="benefit-item">
              <svg className="benefit-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>Free SSL certificate</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="domain-management">
      {/* Domain Header */}
      <div className="domain-header">
        <div className="domain-info">
          <div className="domain-icon">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
            </svg>
          </div>
          <div>
            <h2 className="domain-name">{domainStatus.domain}</h2>
            <p className="domain-subtitle">Custom Domain</p>
          </div>
        </div>
        
        <button
          className="btn-remove"
          onClick={() => setShowRemoveConfirm(true)}
        >
          <svg className="btn-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
          Disconnect
        </button>
      </div>

      {/* Status Cards */}
      <div className="status-grid">
        {/* Verification Status */}
        <div className="status-card">
          <div className="status-card-header">
            <span className="status-card-title">Verification</span>
            <span className={`status-badge ${getStatusColor(domainStatus.verification_status)}`}>
              {domainStatus.verified ? 'Verified' : 'Pending'}
            </span>
          </div>
          <div className="status-card-content">
            {domainStatus.verified ? (
              <div className="status-detail">
                <svg className="status-icon success" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <div className="status-value">Domain Verified</div>
                  <div className="status-label">Verified {formatDate(domainStatus.verified_at)}</div>
                </div>
              </div>
            ) : (
              <div className="status-detail">
                <svg className="status-icon warning" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <div className="status-value">Pending Verification</div>
                  <div className="status-label">{domainStatus.verification_attempts} attempts</div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* SSL Status */}
        <div className="status-card">
          <div className="status-card-header">
            <span className="status-card-title">SSL Certificate</span>
            <span className={`status-badge ${getSSLStatusColor(domainStatus.ssl_status)}`}>
              {domainStatus.ssl_status || 'Pending'}
            </span>
          </div>
          <div className="status-card-content">
            {domainStatus.ssl_status === 'active' ? (
              <div className="status-detail">
                <svg className="status-icon success" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                <div>
                  <div className="status-value">HTTPS Active</div>
                  <div className="status-label">
                    {domainStatus.ssl_expires ? `Expires ${formatDate(domainStatus.ssl_expires)}` : 'Auto-renewing'}
                  </div>
                </div>
              </div>
            ) : (
              <div className="status-detail">
                <svg className="status-icon warning" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <div className="status-value">Provisioning SSL</div>
                  <div className="status-label">Usually takes 5-10 minutes</div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* URLs */}
      <div className="urls-section">
        <h3 className="section-title">Your Site URLs</h3>
        <div className="url-list">
          <div className="url-item">
            <div className="url-label">Custom Domain</div>
            <a
              href={`https://${domainStatus.domain}`}
              target="_blank"
              rel="noopener noreferrer"
              className="url-link"
            >
              https://{domainStatus.domain}
              <svg className="external-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>
          <div className="url-item">
            <div className="url-label">Default URL</div>
            <a
              href={`https://sites.lavish.solutions/site-${siteId.substring(0, 8)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="url-link secondary"
            >
              https://sites.lavish.solutions/site-{siteId.substring(0, 8)}
              <svg className="external-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>
        </div>
      </div>

      {/* DNS Records (if available) */}
      {domainStatus.dns_records && (
        <div className="dns-section">
          <h3 className="section-title">DNS Records Found</h3>
          <div className="dns-records">
            <pre className="dns-code">
              {JSON.stringify(domainStatus.dns_records, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* Last Checked */}
      <div className="info-footer">
        <svg className="info-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>Last checked: {formatDate(domainStatus.last_checked)}</span>
      </div>

      {/* Error Message */}
      {error && (
        <div className="error-message">
          <svg className="error-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {error}
        </div>
      )}

      {/* Remove Confirmation Modal */}
      {showRemoveConfirm && (
        <div className="modal-backdrop" onClick={() => setShowRemoveConfirm(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3 className="modal-title">Disconnect Custom Domain?</h3>
            <p className="modal-description">
              Are you sure you want to disconnect <strong>{domainStatus.domain}</strong>? 
              Your site will still be accessible at the default URL.
            </p>
            
            <div className="modal-actions">
              <button
                className="btn-cancel"
                onClick={() => setShowRemoveConfirm(false)}
                disabled={isRemoving}
              >
                Cancel
              </button>
              <button
                className="btn-danger"
                onClick={handleRemoveDomain}
                disabled={isRemoving}
              >
                {isRemoving ? (
                  <>
                    <svg className="spinner" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Removing...
                  </>
                ) : (
                  'Yes, Disconnect'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

