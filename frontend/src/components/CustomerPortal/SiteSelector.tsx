/**
 * Site Selector Component
 * 
 * Dropdown to select which site when customer owns multiple websites.
 * Used in ticket creation and other site-specific operations.
 * 
 * Author: WebMagic Team
 * Date: January 24, 2026
 */
import React from 'react'
import './SiteSelector.css'

interface Site {
  site_id: string
  slug: string
  site_title: string
  is_primary: boolean
  status?: string
  subscription_status?: string
}

interface SiteSelectorProps {
  sites: Site[]
  selectedSiteId: string
  onSelect: (siteId: string) => void
  label?: string
  required?: boolean
  disabled?: boolean
  showStatus?: boolean
  error?: string
}

const SiteSelector: React.FC<SiteSelectorProps> = ({
  sites,
  selectedSiteId,
  onSelect,
  label = 'Which website is this for?',
  required = true,
  disabled = false,
  showStatus = true,
  error
}) => {
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onSelect(e.target.value)
  }

  return (
    <div className="site-selector-container">
      <label htmlFor="site-selector" className="site-selector-label">
        {label}
        {required && <span className="required-indicator"> *</span>}
      </label>
      
      <div className="site-selector-wrapper">
        <svg
          className="site-selector-icon"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
          <line x1="9" y1="3" x2="9" y2="21"/>
        </svg>
        
        <select
          id="site-selector"
          className={`site-selector ${error ? 'has-error' : ''}`}
          value={selectedSiteId}
          onChange={handleChange}
          required={required}
          disabled={disabled || sites.length === 0}
        >
          <option value="">
            {sites.length === 0 ? 'No sites available' : '-- Select a website --'}
          </option>
          
          {sites.map((site) => (
            <option key={site.site_id} value={site.site_id}>
              {site.site_title || site.slug}
              {site.is_primary ? ' (Primary)' : ''}
              {showStatus && site.status ? ` • ${site.status}` : ''}
            </option>
          ))}
        </select>
      </div>
      
      {error && (
        <p className="site-selector-error">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          {error}
        </p>
      )}
      
      {sites.length > 1 && !error && (
        <p className="site-selector-hint">
          {sites.find(s => s.is_primary) 
            ? 'Your primary site is pre-selected. Change if needed.'
            : 'Please select which website this is related to.'}
        </p>
      )}
    </div>
  )
}

export default SiteSelector
