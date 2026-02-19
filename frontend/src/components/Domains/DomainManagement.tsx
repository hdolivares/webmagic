/**
 * DomainManagement Component
 *
 * Dashboard for managing a connected custom domain.
 * When the domain is not yet verified it surfaces the DNS record
 * instructions and a "Check Verification" button so customers can
 * retry verification at any time without having to disconnect and
 * re-add the domain.
 */
import { useState, useEffect } from 'react'
import { api } from '@/services/api'
import './DomainManagement.css'

interface DomainManagementProps {
  siteId: string
  /** Called after the domain is successfully disconnected so the parent can switch views. */
  onDisconnected?: () => void
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
  verification_token: string | null
  verification_method: string | null
}

// ─── helpers ────────────────────────────────────────────────────────────────

function buildDnsRecord(
  domain: string,
  token: string,
  method: string
): { type: string; host: string; value: string; ttl: number } {
  if (method === 'dns_cname') {
    return {
      type: 'CNAME',
      host: `verify.${domain}`,
      value: `verify.webmagic.io`,
      ttl: 3600,
    }
  }
  return {
    type: 'TXT',
    host: `_webmagic-verify.${domain}`,
    value: `webmagic-verification=${token}`,
    ttl: 3600,
  }
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'verified': return 'status-success'
    case 'pending':  return 'status-warning'
    case 'failed':   return 'status-error'
    default:         return 'status-default'
  }
}

function getSSLStatusColor(status: string | null): string {
  if (!status) return 'status-default'
  switch (status) {
    case 'active':       return 'status-success'
    case 'provisioning': return 'status-warning'
    case 'failed':       return 'status-error'
    default:             return 'status-default'
  }
}

function formatDate(dateString: string | null): string {
  if (!dateString) return 'Never'
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

// ─── component ──────────────────────────────────────────────────────────────

export function DomainManagement({ siteId, onDisconnected }: DomainManagementProps) {
  const [domainStatus, setDomainStatus] = useState<DomainStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isRemoving, setIsRemoving] = useState(false)
  const [showRemoveConfirm, setShowRemoveConfirm] = useState(false)
  const [isVerifying, setIsVerifying] = useState(false)
  const [verifyResult, setVerifyResult] = useState<{ success: boolean; message: string } | null>(null)
  const [copiedField, setCopiedField] = useState<string | null>(null)

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
      if (err.response?.status !== 404) {
        setError('Failed to load domain status')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleVerifyDomain = async () => {
    if (!domainStatus) return
    setIsVerifying(true)
    setVerifyResult(null)
    try {
      const response = await api.verifyDomain(siteId, domainStatus.domain)
      if (response.verified) {
        setVerifyResult({ success: true, message: 'Domain verified successfully! SSL provisioning will begin shortly.' })
        // Refresh status to show verified state
        await fetchDomainStatus()
      } else {
        setVerifyResult({
          success: false,
          message: 'DNS record not found yet. DNS changes can take up to 24 hours to propagate — please try again later.',
        })
      }
    } catch (err: any) {
      setVerifyResult({
        success: false,
        message: err.response?.data?.detail || 'Verification check failed. Please try again.',
      })
    } finally {
      setIsVerifying(false)
    }
  }

  const handleRemoveDomain = async () => {
    setIsRemoving(true)
    setError(null)
    try {
      await api.disconnectDomain(siteId)
      setShowRemoveConfirm(false)
      // Let the parent page handle the view switch — don't render an empty
      // state inside this component (which causes the broken layout).
      onDisconnected?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to remove domain. Please try again.')
    } finally {
      setIsRemoving(false)
    }
  }

  const copyToClipboard = async (text: string, fieldId: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedField(fieldId)
      setTimeout(() => setCopiedField(null), 2000)
    } catch {
      // Clipboard API not available — silently ignore
    }
  }

  // ── Loading ──────────────────────────────────────────────────────────────

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

  // No domain — parent (DomainsPage) is responsible for switching to DomainSetup.
  // Render nothing while the transition happens.
  if (!domainStatus) return null

  // ── DNS record for pending verification ──────────────────────────────────

  const dnsRecord =
    !domainStatus.verified &&
    domainStatus.verification_token &&
    domainStatus.verification_method
      ? buildDnsRecord(domainStatus.domain, domainStatus.verification_token, domainStatus.verification_method)
      : null

  // ── Main render ──────────────────────────────────────────────────────────

  return (
    <div className="domain-management">

      {/* Domain header */}
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
        <button className="btn-remove" onClick={() => setShowRemoveConfirm(true)}>
          <svg className="btn-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
          Disconnect
        </button>
      </div>

      {/* ── DNS Instructions (only when not verified) ─── */}
      {dnsRecord && (
        <div className="dns-instructions-panel">
          <div className="dns-instructions-header">
            <svg className="dns-instructions-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h3 className="dns-instructions-title">Add This DNS Record</h3>
              <p className="dns-instructions-subtitle">
                Log in to your domain registrar and add the following record. DNS propagation can take up to 24 hours.
              </p>
            </div>
          </div>

          <div className="dns-record-table">
            {[
              { label: 'Type', value: dnsRecord.type },
              { label: 'Host / Name', value: dnsRecord.host },
              { label: 'Value', value: dnsRecord.value },
              { label: 'TTL', value: String(dnsRecord.ttl) },
            ].map(({ label, value }) => (
              <div key={label} className="dns-record-row">
                <span className="dns-record-label">{label}</span>
                <div className="dns-record-value-wrap">
                  <code className="dns-record-value">{value}</code>
                  <button
                    className="btn-copy"
                    onClick={() => copyToClipboard(value, label)}
                    title="Copy to clipboard"
                  >
                    {copiedField === label ? (
                      <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" width="16" height="16">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    ) : (
                      <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" width="16" height="16">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Verify button + result */}
          <div className="dns-verify-actions">
            <button
              className="btn-verify"
              onClick={handleVerifyDomain}
              disabled={isVerifying}
            >
              {isVerifying ? (
                <>
                  <svg className="spinner" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Checking…
                </>
              ) : (
                <>
                  <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" width="18" height="18">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Check Verification
                </>
              )}
            </button>

            {verifyResult && (
              <div className={`verify-result ${verifyResult.success ? 'verify-result--success' : 'verify-result--error'}`}>
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" width="18" height="18">
                  {verifyResult.success ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  )}
                </svg>
                {verifyResult.message}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Status cards */}
      <div className="status-grid">
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
                  <div className="status-label">
                    {domainStatus.verification_attempts > 0
                      ? `${domainStatus.verification_attempts} check${domainStatus.verification_attempts !== 1 ? 's' : ''} performed`
                      : 'No checks yet — click "Check Verification" above'}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

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
                  <div className="status-label">Starts automatically after verification</div>
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
              href={`https://web.lavish.solutions/${siteId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="url-link secondary"
            >
              https://web.lavish.solutions/{siteId.substring(0, 8)}…
              <svg className="external-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="info-footer">
        <svg className="info-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>Last checked: {formatDate(domainStatus.last_checked)}</span>
      </div>

      {error && (
        <div className="error-message">
          <svg className="error-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {error}
        </div>
      )}

      {/* Disconnect confirmation modal */}
      {showRemoveConfirm && (
        <div className="modal-backdrop" onClick={() => setShowRemoveConfirm(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3 className="modal-title">Disconnect Custom Domain?</h3>
            <p className="modal-description">
              Are you sure you want to disconnect <strong>{domainStatus.domain}</strong>?{' '}
              Your site will still be accessible at the default URL.
            </p>
            <div className="modal-actions">
              <button className="btn-cancel" onClick={() => setShowRemoveConfirm(false)} disabled={isRemoving}>
                Cancel
              </button>
              <button className="btn-danger" onClick={handleRemoveDomain} disabled={isRemoving}>
                {isRemoving ? (
                  <>
                    <svg className="spinner" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Removing…
                  </>
                ) : 'Yes, Disconnect'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
