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
}

type FilterType = 'all' | 'sms_only' | 'email_only' | 'both'

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
}) => {
  const [filter, setFilter] = useState<FilterType>('all')

  // Filter businesses based on selected filter
  const filteredBusinesses = useMemo(() => {
    switch (filter) {
      case 'sms_only':
        return businesses.filter(b => b.phone && !b.email)
      case 'email_only':
        return businesses.filter(b => b.email && !b.phone)
      case 'both':
        return businesses.filter(b => b.email && b.phone)
      default:
        return businesses
    }
  }, [businesses, filter])

  // Calculate stats for filters
  const stats = useMemo(() => {
    const smsOnly = businesses.filter(b => b.phone && !b.email).length
    const emailOnly = businesses.filter(b => b.email && !b.phone).length
    const both = businesses.filter(b => b.email && b.phone).length

    return { smsOnly, emailOnly, both, total: businesses.length }
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
        <div style={{ display: 'flex', gap: 'var(--campaigns-spacing-sm)' }}>
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
  children: React.ReactNode
}

const FilterButton: React.FC<FilterButtonProps> = ({ active, onClick, count, icon, children }) => (
  <button
    type="button"
    onClick={onClick}
    style={{
      padding: '0.375rem 0.75rem',
      borderRadius: 'var(--campaigns-radius-md)',
      border: '1px solid var(--color-border-primary)',
      background: active ? 'var(--campaigns-selected-bg)' : 'transparent',
      color: active ? 'var(--campaigns-selected-border)' : 'var(--color-text-secondary)',
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
        background: active ? 'var(--campaigns-selected-border)' : 'var(--color-bg-secondary)',
        color: active ? 'white' : 'var(--color-text-secondary)',
      }}
    >
      {count}
    </span>
  </button>
)

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
  const handleClick = (e: React.MouseEvent) => {
    // If clicking the checkbox area, toggle selection
    if ((e.target as HTMLElement).closest('.business-item__checkbox')) {
      onToggle()
    } else {
      // Otherwise trigger the preview
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
          {business.phone && (
            <span className="business-item__badge business-item__badge--sms">
              💬 SMS
            </span>
          )}
          {business.email && (
            <span className="business-item__badge business-item__badge--email">
              📧 Email
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

export default ReadyBusinessesPanel
