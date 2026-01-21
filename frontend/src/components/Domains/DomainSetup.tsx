/**
 * DomainSetup Component
 * 
 * Multi-step wizard for connecting custom domains.
 * Guides customers through domain verification process.
 * 
 * Author: WebMagic Team
 * Date: January 21, 2026
 */
import { useState } from 'react'
import { api } from '@/services/api'
import './DomainSetup.css'

interface DomainSetupProps {
  siteId: string
  onComplete?: (domain: string) => void
  onCancel?: () => void
}

type Step = 'enter' | 'method' | 'instructions' | 'verify' | 'complete'

interface DNSRecord {
  record_type: string
  host: string
  value: string
  ttl: number
}

export function DomainSetup({ siteId, onComplete, onCancel }: DomainSetupProps) {
  const [currentStep, setCurrentStep] = useState<Step>('enter')
  const [domain, setDomain] = useState('')
  const [verificationMethod, setVerificationMethod] = useState<'dns_txt' | 'dns_cname'>('dns_txt')
  const [dnsRecord, setDnsRecord] = useState<DNSRecord | null>(null)
  const [instructions, setInstructions] = useState('')
  const [verificationToken, setVerificationToken] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [verifying, setVerifying] = useState(false)
  const [verifyAttempts, setVerifyAttempts] = useState(0)

  const handleDomainSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    
    if (!domain.trim()) {
      setError('Please enter a domain name')
      return
    }

    setIsLoading(true)

    try {
      const response = await api.connectDomain(siteId, {
        domain: domain.trim(),
        verification_method: verificationMethod
      })

      setDnsRecord(response.dns_records)
      setInstructions(response.instructions)
      setVerificationToken(response.verification_token)
      setCurrentStep('instructions')
    } catch (err: any) {
      console.error('Failed to connect domain:', err)
      setError(err.response?.data?.detail || 'Failed to connect domain. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleVerifyDomain = async () => {
    setError(null)
    setVerifying(true)
    setVerifyAttempts(prev => prev + 1)

    try {
      const response = await api.verifyDomain(siteId, domain)

      if (response.verified) {
        setCurrentStep('complete')
        setTimeout(() => {
          onComplete?.(domain)
        }, 2000)
      } else {
        setError(
          response.message || 
          'Domain verification failed. Please ensure DNS records are correctly configured. DNS propagation can take up to 24 hours.'
        )
      }
    } catch (err: any) {
      console.error('Failed to verify domain:', err)
      setError(err.response?.data?.detail || 'Failed to verify domain. Please try again.')
    } finally {
      setVerifying(false)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    // Could add toast notification here
  }

  const renderStepIndicator = () => {
    const steps = [
      { id: 'enter', label: 'Enter Domain' },
      { id: 'method', label: 'Choose Method' },
      { id: 'instructions', label: 'Add DNS Records' },
      { id: 'verify', label: 'Verify' },
      { id: 'complete', label: 'Complete' }
    ]

    const currentIndex = steps.findIndex(s => s.id === currentStep)

    return (
      <div className="step-indicator">
        {steps.map((step, index) => (
          <div
            key={step.id}
            className={`step-item ${index <= currentIndex ? 'active' : ''} ${index < currentIndex ? 'completed' : ''}`}
          >
            <div className="step-number">
              {index < currentIndex ? (
                <svg className="check-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                index + 1
              )}
            </div>
            <div className="step-label">{step.label}</div>
          </div>
        ))}
      </div>
    )
  }

  const renderEnterDomain = () => (
    <div className="wizard-content">
      <h2 className="wizard-title">Connect Your Custom Domain</h2>
      <p className="wizard-description">
        Enter your domain name to get started. We'll guide you through the verification process.
      </p>

      <form onSubmit={handleDomainSubmit} className="domain-form">
        <div className="form-group">
          <label htmlFor="domain" className="form-label">
            Domain Name
            <span className="required">*</span>
          </label>
          <input
            id="domain"
            type="text"
            className="form-input"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            placeholder="example.com"
            disabled={isLoading}
            autoFocus
          />
          <div className="form-hint">
            Enter your domain without "www" or "http://" (e.g., example.com)
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Verification Method</label>
          <div className="method-options">
            <label className={`method-card ${verificationMethod === 'dns_txt' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="method"
                value="dns_txt"
                checked={verificationMethod === 'dns_txt'}
                onChange={(e) => setVerificationMethod(e.target.value as 'dns_txt')}
                disabled={isLoading}
              />
              <div className="method-content">
                <div className="method-title">TXT Record (Recommended)</div>
                <div className="method-description">
                  Safer option, no downtime during verification
                </div>
              </div>
            </label>

            <label className={`method-card ${verificationMethod === 'dns_cname' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="method"
                value="dns_cname"
                checked={verificationMethod === 'dns_cname'}
                onChange={(e) => setVerificationMethod(e.target.value as 'dns_cname')}
                disabled={isLoading}
              />
              <div className="method-content">
                <div className="method-title">CNAME Record</div>
                <div className="method-description">
                  Simpler for some DNS providers
                </div>
              </div>
            </label>
          </div>
        </div>

        {error && (
          <div className="error-message">
            <svg className="error-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {error}
          </div>
        )}

        <div className="wizard-actions">
          {onCancel && (
            <button type="button" className="btn-cancel" onClick={onCancel} disabled={isLoading}>
              Cancel
            </button>
          )}
          <button type="submit" className="btn-primary" disabled={isLoading}>
            {isLoading ? (
              <>
                <svg className="spinner" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Processing...
              </>
            ) : (
              'Continue'
            )}
          </button>
        </div>
      </form>
    </div>
  )

  const renderInstructions = () => (
    <div className="wizard-content">
      <h2 className="wizard-title">Add DNS Records</h2>
      <p className="wizard-description">
        Add the following DNS record to your domain's DNS settings. This verifies that you own the domain.
      </p>

      <div className="dns-record-card">
        <div className="dns-record-header">
          <span className="dns-record-type">{dnsRecord?.record_type}</span>
          <span className="dns-domain">{domain}</span>
        </div>

        <div className="dns-record-fields">
          <div className="dns-field">
            <label className="dns-field-label">Host/Name</label>
            <div className="dns-field-value">
              <code>{dnsRecord?.host}</code>
              <button
                className="btn-copy"
                onClick={() => copyToClipboard(dnsRecord?.host || '')}
                title="Copy to clipboard"
              >
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
            </div>
          </div>

          <div className="dns-field">
            <label className="dns-field-label">Type</label>
            <div className="dns-field-value">
              <code>{dnsRecord?.record_type}</code>
            </div>
          </div>

          <div className="dns-field">
            <label className="dns-field-label">Value</label>
            <div className="dns-field-value">
              <code className="dns-value-long">{dnsRecord?.value}</code>
              <button
                className="btn-copy"
                onClick={() => copyToClipboard(dnsRecord?.value || '')}
                title="Copy to clipboard"
              >
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
            </div>
          </div>

          <div className="dns-field">
            <label className="dns-field-label">TTL</label>
            <div className="dns-field-value">
              <code>{dnsRecord?.ttl} (1 hour)</code>
            </div>
          </div>
        </div>
      </div>

      <div className="instructions-box">
        <h3>Step-by-Step Instructions:</h3>
        <ol>
          <li>Log in to your domain registrar (GoDaddy, Namecheap, etc.)</li>
          <li>Find the DNS management or DNS settings page</li>
          <li>Add a new {dnsRecord?.record_type} record with the values shown above</li>
          <li>Save the changes (may take up to 24 hours to propagate)</li>
          <li>Return here and click "Verify Domain" to complete setup</li>
        </ol>
      </div>

      {error && (
        <div className="error-message">
          <svg className="error-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {error}
        </div>
      )}

      <div className="wizard-actions">
        <button
          type="button"
          className="btn-secondary"
          onClick={() => setCurrentStep('enter')}
          disabled={verifying}
        >
          Back
        </button>
        <button
          type="button"
          className="btn-primary"
          onClick={handleVerifyDomain}
          disabled={verifying}
        >
          {verifying ? (
            <>
              <svg className="spinner" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Verifying... (Attempt {verifyAttempts})
            </>
          ) : (
            'Verify Domain'
          )}
        </button>
      </div>

      <div className="info-box">
        <svg className="info-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div>
          <strong>DNS Propagation:</strong> DNS changes can take anywhere from a few minutes to 24 hours to propagate globally. 
          If verification fails, wait a while and try again.
        </div>
      </div>
    </div>
  )

  const renderComplete = () => (
    <div className="wizard-content complete">
      <div className="success-icon-wrapper">
        <svg className="success-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>

      <h2 className="wizard-title">Domain Connected! 🎉</h2>
      <p className="wizard-description">
        Your custom domain <strong>{domain}</strong> has been successfully verified and connected.
      </p>

      <div className="complete-info">
        <div className="complete-step">
          <svg className="complete-check" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span>Domain verified</span>
        </div>
        <div className="complete-step">
          <svg className="complete-check" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span>SSL certificate provisioning (5-10 minutes)</span>
        </div>
        <div className="complete-step">
          <svg className="complete-check" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span>Site will be accessible at your domain</span>
        </div>
      </div>

      <div className="info-box">
        <svg className="info-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div>
          Your site will be accessible at <strong>https://{domain}</strong> within the next 10 minutes. 
          SSL certificate is being provisioned automatically.
        </div>
      </div>
    </div>
  )

  return (
    <div className="domain-setup">
      {renderStepIndicator()}
      
      <div className="wizard-container">
        {currentStep === 'enter' && renderEnterDomain()}
        {currentStep === 'instructions' && renderInstructions()}
        {currentStep === 'complete' && renderComplete()}
      </div>
    </div>
  )
}

