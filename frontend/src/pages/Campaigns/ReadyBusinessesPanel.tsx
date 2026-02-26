/**
 * ReadyBusinessesPanel Component
 * 
 * Displays businesses with completed sites ready for campaigns
 * Supports bulk selection, filtering, and channel display
 * Following best practices: Separation of concerns, accessibility, performance
 */
import React, { useState, useMemo } from 'react'
import type { ReadyBusiness } from '@/types'
import './Campaigns.css'

interface ReadyBusinessesPanelProps {
  businesses: ReadyBusiness[]
  selectedIds: string[]
  /** ID of business currently being previewed (highlight in list) */
  previewBusinessId?: string | null
  onSelectionChange: (selectedIds: string[]) => void
  onBusinessClick?: (business: ReadyBusiness) => void
  isLoading: boolean
  showContacted: boolean
  onToggleContacted: () => void
  alreadyContactedCount: number
}

type FilterType = 'all' | 'sms_only' | 'email_only' | 'both' | 'call_later'

const CAMPAIGN_STATUS_COLORS: Record<string, string> = {
  delivered: '#16a34a',
  sent: '#2563eb',
  pending: '#d97706',
  scheduled: '#7c3aed',
  failed: '#dc2626',
  bounced: '#dc2626',
  opened: '#0891b2',
  clicked: '#0891b2',
  replied: '#16a34a',
}

/**
 * ReadyBusinessesPanel - Select businesses for campaign creation
 */
export const ReadyBusinessesPanel: React.FC<ReadyBusinessesPanelProps> = ({
  businesses,
  selectedIds,
  previewBusinessId = null,
  onSelectionChange,
  onBusinessClick,
  isLoading,
  showContacted,
  onToggleContacted,
  alreadyContactedCount,
}) => {
  const [filter, setFilter] = useState<FilterType>('all')

  // Filter businesses based on selected filter
  const filteredBusinesses = useMemo(() => {
    switch (filter) {
      case 'sms_only':
        return businesses.filter(b => b.phone && !b.email && b.outreach_channel !== 'call_later')
      case 'email_only':
        return businesses.filter(b => b.email && !b.phone)
      case 'both':
        return businesses.filter(b => b.email && b.phone)
      case 'call_later':
        return businesses.filter(b => b.outreach_channel === 'call_later')
      default:
        return businesses
    }
  }, [businesses, filter])

  // Calculate stats for filters
  const stats = useMemo(() => {
    const smsOnly = businesses.filter(b => b.phone && !b.email && b.outreach_channel !== 'call_later').length
    const emailOnly = businesses.filter(b => b.email && !b.phone).length
    const both = businesses.filter(b => b.email && b.phone).length
    const callLater = businesses.filter(b => b.outreach_channel === 'call_later').length

    return { smsOnly, emailOnly, both, callLater, total: businesses.length }
  }, [businesses])

  // Toggle business selection
  const handleBusinessToggle = (businessId: string) => {
    const isSelected = selectedIds.includes(businessId)
    
    if (isSelected) {
      onSelectionChange(selectedIds.filter(id => id !== businessId))
    } else {
      onSelectionChange([...selectedIds, businessId])
    }
  }

  // Select all filtered businesses
  const handleSelectAll = () => {
    const filteredIds = filteredBusinesses.map(b => b.id)
    const allSelected = filteredIds.every(id => selectedIds.includes(id))

    if (allSelected) {
      // Deselect all filtered businesses
      onSelectionChange(selectedIds.filter(id => !filteredIds.includes(id)))
    } else {
      // Select all filtered businesses (merge with existing)
      const newSelected = [...new Set([...selectedIds, ...filteredIds])]
      onSelectionChange(newSelected)
    }
  }

  // Clear all selections
  const handleClearSelection = () => {
    onSelectionChange([])
  }

  // Check if all filtered businesses are selected
  const allFilteredSelected = filteredBusinesses.length > 0 && 
    filteredBusinesses.every(b => selectedIds.includes(b.id))

  // Loading state
  if (isLoading) {
    return (
      <div className="campaigns-card">
        <div className="campaigns-card__header">
          <h3 className="campaigns-card__title">Ready for Campaigns</h3>
        </div>
        <div className="campaigns-card__body">
          <div className="campaigns-loading">
            <div className="spinner" />
            <span style={{ marginLeft: '0.5rem' }}>Loading businesses...</span>
          </div>
        </div>
      </div>
    )
  }

  // Empty state
  if (businesses.length === 0) {
    return (
      <div className="campaigns-card">
        <div className="campaigns-card__header">
          <h3 className="campaigns-card__title">Ready for Campaigns</h3>
        </div>
        <div className="campaigns-card__body">
          <div className="campaigns-empty">
            <div className="campaigns-empty__icon">🎯</div>
            <h4 className="campaigns-empty__title">No Businesses Ready</h4>
            <p className="campaigns-empty__description">
              Generate websites for businesses first, then they'll appear here ready for campaigns.
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="campaigns-card">
      {/* Header with Selection Actions */}
      <div className="campaigns-card__header">
        <h3 className="campaigns-card__title">
          Ready for Campaigns ({filteredBusinesses.length})
        </h3>
        <div style={{ display: 'flex', gap: 'var(--campaigns-spacing-sm)', alignItems: 'center' }}>
          <button
            type="button"
            onClick={onToggleContacted}
            title={showContacted ? 'Hide already-contacted businesses' : `Show ${alreadyContactedCount} already-contacted`}
            style={{
              padding: '0.375rem 0.625rem',
              fontSize: '0.7rem',
              borderRadius: 'var(--campaigns-radius-md)',
              border: '1px solid var(--color-border-primary)',
              background: showContacted ? '#fef3c7' : 'transparent',
              color: showContacted ? '#92400e' : 'var(--color-text-secondary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.25rem',
            }}
          >
            {showContacted ? '✓ Showing contacted' : `+ ${alreadyContactedCount} contacted`}
          </button>
          <button
            type="button"
            className="campaigns-button campaigns-button--secondary"
            onClick={handleSelectAll}
            disabled={filteredBusinesses.length === 0}
            style={{ padding: '0.375rem 0.75rem', fontSize: '0.75rem' }}
          >
            {allFilteredSelected ? 'Deselect All' : 'Select All'}
          </button>
          {selectedIds.length > 0 && (
            <button
              type="button"
              className="campaigns-button campaigns-button--secondary"
              onClick={handleClearSelection}
              style={{ padding: '0.375rem 0.75rem', fontSize: '0.75rem' }}
            >
              Clear ({selectedIds.length})
            </button>
          )}
        </div>
      </div>

      {/* Filter Tabs */}
      <div
        style={{
          padding: 'var(--campaigns-spacing-md) var(--campaigns-spacing-lg)',
          borderBottom: '1px solid var(--color-border-primary)',
          display: 'flex',
          gap: 'var(--campaigns-spacing-sm)',
        }}
      >
        <FilterButton
          active={filter === 'all'}
          onClick={() => setFilter('all')}
          count={stats.total}
        >
          All
        </FilterButton>
        <FilterButton
          active={filter === 'sms_only'}
          onClick={() => setFilter('sms_only')}
          count={stats.smsOnly}
          icon="💬"
        >
          SMS Only
        </FilterButton>
        <FilterButton
          active={filter === 'email_only'}
          onClick={() => setFilter('email_only')}
          count={stats.emailOnly}
          icon="📧"
        >
          Email Only
        </FilterButton>
        <FilterButton
          active={filter === 'both'}
          onClick={() => setFilter('both')}
          count={stats.both}
          icon="📧💬"
        >
          Both
        </FilterButton>
        {stats.callLater > 0 && (
          <FilterButton
            active={filter === 'call_later'}
            onClick={() => setFilter('call_later')}
            count={stats.callLater}
            icon="📞"
            variant="warning"
          >
            Call Later
          </FilterButton>
        )}
      </div>

      {/* Business List */}
      <div className="campaigns-card__body">
        {filteredBusinesses.length === 0 ? (
          <div className="campaigns-empty" style={{ padding: '2rem 1rem' }}>
            <p className="campaigns-empty__description">
              No businesses match this filter
            </p>
          </div>
        ) : (
          <div className="business-list">
            {filteredBusinesses.map((business) => (
              <BusinessItem
                key={business.id}
                business={business}
                isSelected={selectedIds.includes(business.id)}
                isPreviewing={previewBusinessId === business.id}
                onToggle={() => handleBusinessToggle(business.id)}
                onClick={() => onBusinessClick?.(business)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer with Selection Summary */}
      {selectedIds.length > 0 && (
        <div className="campaigns-card__footer">
          <div style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
            {selectedIds.length} {selectedIds.length === 1 ? 'business' : 'businesses'} selected
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * FilterButton - Reusable filter button component
 */
interface FilterButtonProps {
  active: boolean
  onClick: () => void
  count: number
  icon?: string
  variant?: 'default' | 'warning'
  children: React.ReactNode
}

const FilterButton: React.FC<FilterButtonProps> = ({ active, onClick, count, icon, variant = 'default', children }) => {
  const isWarning = variant === 'warning'
  const activeColor = isWarning ? '#d97706' : 'var(--campaigns-selected-border)'
  const activeBg = isWarning ? '#fef3c7' : 'var(--campaigns-selected-bg)'
  const activeBadgeBg = isWarning ? '#d97706' : 'var(--campaigns-selected-border)'

  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        padding: '0.375rem 0.75rem',
        borderRadius: 'var(--campaigns-radius-md)',
        border: `1px solid ${active && isWarning ? '#d97706' : 'var(--color-border-primary)'}`,
        background: active ? activeBg : 'transparent',
        color: active ? activeColor : 'var(--color-text-secondary)',
        fontWeight: active ? 'var(--campaigns-font-weight-medium)' : 'var(--campaigns-font-weight-normal)',
        fontSize: '0.875rem',
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        display: 'flex',
        alignItems: 'center',
        gap: '0.375rem',
      }}
    >
      {icon && <span>{icon}</span>}
      <span>{children}</span>
      <span
        style={{
          fontSize: '0.75rem',
          padding: '0.125rem 0.375rem',
          borderRadius: 'var(--campaigns-radius-full)',
          background: active ? activeBadgeBg : 'var(--color-bg-secondary)',
          color: active ? 'white' : 'var(--color-text-secondary)',
        }}
      >
        {count}
      </span>
    </button>
  )
}

/**
 * BusinessItem - Individual business row component
 */
interface BusinessItemProps {
  business: ReadyBusiness
  isSelected: boolean
  isPreviewing?: boolean
  onToggle: () => void
  onClick: () => void
}

const BusinessItem: React.FC<BusinessItemProps> = ({ business, isSelected, isPreviewing, onToggle, onClick }) => {
  const campaignStatus = business.last_campaign_status
  const statusColor = campaignStatus ? (CAMPAIGN_STATUS_COLORS[campaignStatus] ?? '#6b7280') : null
  const isCallLater = business.outreach_channel === 'call_later'

  const handleClick = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('.business-item__checkbox')) {
      onToggle()
    } else {
      onClick()
    }
  }

  return (
    <div
      className={`business-item ${isSelected ? 'business-item--selected' : ''} ${isPreviewing ? 'business-item--previewing' : ''}`}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyPress={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onToggle()
        }
      }}
      style={isCallLater ? { opacity: 0.75 } : undefined}
    >
      {/* Checkbox */}
      <div className="business-item__checkbox">
        {isSelected && <span>✓</span>}
      </div>

      {/* Business Info */}
      <div className="business-item__info">
        <h4 className="business-item__name">{business.name}</h4>
        <div className="business-item__meta">
          {/* Location */}
          {(business.city || business.state) && (
            <span>
              📍 {business.city}{business.city && business.state && ', '}{business.state}
            </span>
          )}

          {/* Rating */}
          {business.rating && (
            <span>⭐ {business.rating.toFixed(1)}</span>
          )}

          {/* Channel badges */}
          {business.phone && !isCallLater && (
            <span className="business-item__badge business-item__badge--sms">
              💬 SMS
            </span>
          )}
          {isCallLater && (
            <span
              title={`Landline number — cannot receive SMS (${business.phone_line_type ?? 'landline'})`}
              style={{
                fontSize: '0.65rem',
                padding: '0.1rem 0.4rem',
                borderRadius: '9999px',
                background: '#fef3c718',
                color: '#92400e',
                border: '1px solid #d9780640',
                fontWeight: 600,
              }}
            >
              📞 Landline
            </span>
          )}
          {business.email && (
            <span className="business-item__badge business-item__badge--email">
              📧 Email
            </span>
          )}
          {/* Last campaign status badge */}
          {campaignStatus && statusColor && (
            <span style={{
              fontSize: '0.65rem',
              padding: '0.1rem 0.4rem',
              borderRadius: '9999px',
              background: `${statusColor}18`,
              color: statusColor,
              border: `1px solid ${statusColor}40`,
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.03em',
            }}>
              {campaignStatus}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

export default ReadyBusinessesPanel
