/**
 * CRM Filter Bar Component
 * 
 * Advanced filtering interface with preset buttons and custom filters.
 * Supports quick filter presets and detailed filtering options.
 * 
 * @author WebMagic Team
 * @date January 22, 2026
 */
import React, { useState } from 'react'
import { Filter, X, Flame, Mail, MessageSquare, Phone, AlertCircle, CheckCircle2 } from 'lucide-react'
import './FilterBar.css'

export interface BusinessFilters {
  // Contact data
  has_email?: boolean
  has_phone?: boolean
  
  // Contact status
  contact_status?: string
  was_contacted?: boolean
  is_customer?: boolean
  is_bounced?: boolean
  is_unsubscribed?: boolean
  
  // Website status
  website_status?: string
  has_site?: boolean
  
  // Qualification
  min_score?: number
  max_score?: number
  min_rating?: number
  min_reviews?: number
  
  // Basic filters
  category?: string
  city?: string
  state?: string
}

export interface FilterPreset {
  id: string
  label: string
  icon: React.ReactNode
  description: string
  filters: BusinessFilters
}

export interface FilterBarProps {
  filters: BusinessFilters
  onFiltersChange: (filters: BusinessFilters) => void
  resultCount?: number
  className?: string
}

/**
 * Preset filter configurations
 */
const FILTER_PRESETS: FilterPreset[] = [
  {
    id: 'hot-leads',
    label: 'Hot Leads',
    icon: <Flame className="w-4 h-4" />,
    description: 'High-scoring leads not yet contacted',
    filters: {
      min_score: 70,
      was_contacted: false,
    },
  },
  {
    id: 'needs-email',
    label: 'Needs Email',
    icon: <Mail className="w-4 h-4" />,
    description: 'Has phone, missing email',
    filters: {
      has_phone: true,
      has_email: false,
    },
  },
  {
    id: 'needs-sms',
    label: 'Needs SMS',
    icon: <Phone className="w-4 h-4" />,
    description: 'Has email, missing phone',
    filters: {
      has_email: true,
      has_phone: false,
    },
  },
  {
    id: 'follow-up',
    label: 'Follow Up',
    icon: <MessageSquare className="w-4 h-4" />,
    description: 'Contacted but no reply',
    filters: {
      was_contacted: true,
      contact_status: 'emailed',
    },
  },
  {
    id: 'bounced',
    label: 'Bounced',
    icon: <AlertCircle className="w-4 h-4" />,
    description: 'Failed contacts to clean up',
    filters: {
      is_bounced: true,
    },
  },
  {
    id: 'customers',
    label: 'Customers',
    icon: <CheckCircle2 className="w-4 h-4" />,
    description: 'Paying customers',
    filters: {
      is_customer: true,
    },
  },
]

/**
 * FilterBar Component
 * 
 * Usage:
 * ```tsx
 * const [filters, setFilters] = useState<BusinessFilters>({})
 * 
 * <FilterBar
 *   filters={filters}
 *   onFiltersChange={setFilters}
 *   resultCount={126}
 * />
 * ```
 */
export const FilterBar: React.FC<FilterBarProps> = ({
  filters,
  onFiltersChange,
  resultCount,
  className = '',
}) => {
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [activePreset, setActivePreset] = useState<string | null>(null)

  // Apply preset filter
  const applyPreset = (preset: FilterPreset) => {
    setActivePreset(preset.id)
    onFiltersChange(preset.filters)
  }

  // Clear all filters
  const clearFilters = () => {
    setActivePreset(null)
    onFiltersChange({})
  }

  // Update individual filter
  const updateFilter = (key: keyof BusinessFilters, value: any) => {
    setActivePreset(null) // Clear preset when manually filtering
    onFiltersChange({
      ...filters,
      [key]: value,
    })
  }

  // Count active filters
  const activeFilterCount = Object.keys(filters).filter(
    (key) => filters[key as keyof BusinessFilters] !== undefined
  ).length

  return (
    <div className={`crm-filter-bar ${className}`}>
      {/* Header with result count */}
      <div className="filter-bar-header">
        <div className="filter-icon-wrapper">
          <Filter className="filter-icon" />
          <span className="filter-title">Filters</span>
        </div>
        
        {resultCount !== undefined && (
          <span className="result-count">
            {resultCount} result{resultCount !== 1 ? 's' : ''}
          </span>
        )}

        {activeFilterCount > 0 && (
          <button
            onClick={clearFilters}
            className="btn-clear-filters"
            title="Clear all filters"
          >
            <X className="w-4 h-4" />
            Clear
          </button>
        )}
      </div>

      {/* Quick Presets */}
      <div className="filter-presets">
        {FILTER_PRESETS.map((preset) => (
          <button
            key={preset.id}
            onClick={() => applyPreset(preset)}
            className={`filter-preset-btn ${activePreset === preset.id ? 'active' : ''}`}
            title={preset.description}
          >
            {preset.icon}
            <span>{preset.label}</span>
          </button>
        ))}
      </div>

      {/* Advanced Filters Toggle */}
      <div className="filter-section">
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="btn-toggle-advanced"
        >
          <Filter className="w-4 h-4" />
          Advanced Filters
          <span className={`toggle-icon ${showAdvanced ? 'open' : ''}`}>▼</span>
        </button>
      </div>

      {/* Advanced Filters Panel */}
      {showAdvanced && (
        <div className="filter-advanced-panel">
          {/* Contact Data Filters */}
          <div className="filter-group">
            <h4 className="filter-group-title">Contact Information</h4>
            <div className="filter-row">
              <label className="filter-checkbox">
                <input
                  type="checkbox"
                  checked={filters.has_email === true}
                  onChange={(e) => updateFilter('has_email', e.target.checked ? true : undefined)}
                />
                <span>Has Email</span>
              </label>
              <label className="filter-checkbox">
                <input
                  type="checkbox"
                  checked={filters.has_phone === true}
                  onChange={(e) => updateFilter('has_phone', e.target.checked ? true : undefined)}
                />
                <span>Has Phone</span>
              </label>
            </div>
          </div>

          {/* Contact Status Filters */}
          <div className="filter-group">
            <h4 className="filter-group-title">Contact Status</h4>
            <div className="filter-row">
              <select
                value={filters.contact_status || ''}
                onChange={(e) => updateFilter('contact_status', e.target.value || undefined)}
                className="filter-select"
              >
                <option value="">Any Status</option>
                <option value="pending">Pending</option>
                <option value="emailed">Emailed</option>
                <option value="sms_sent">SMS Sent</option>
                <option value="opened">Opened</option>
                <option value="clicked">Clicked</option>
                <option value="replied">Replied</option>
                <option value="purchased">Purchased</option>
                <option value="bounced">Bounced</option>
                <option value="unsubscribed">Unsubscribed</option>
              </select>
            </div>
            <div className="filter-row">
              <label className="filter-checkbox">
                <input
                  type="checkbox"
                  checked={filters.was_contacted === true}
                  onChange={(e) => updateFilter('was_contacted', e.target.checked ? true : undefined)}
                />
                <span>Was Contacted</span>
              </label>
              <label className="filter-checkbox">
                <input
                  type="checkbox"
                  checked={filters.is_customer === true}
                  onChange={(e) => updateFilter('is_customer', e.target.checked ? true : undefined)}
                />
                <span>Is Customer</span>
              </label>
            </div>
          </div>

          {/* Qualification Filters */}
          <div className="filter-group">
            <h4 className="filter-group-title">Qualification</h4>
            <div className="filter-row">
              <div className="filter-input-group">
                <label className="filter-label">Min Score</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={filters.min_score || ''}
                  onChange={(e) => updateFilter('min_score', e.target.value ? parseInt(e.target.value) : undefined)}
                  className="filter-input"
                  placeholder="0-100"
                />
              </div>
              <div className="filter-input-group">
                <label className="filter-label">Min Rating</label>
                <input
                  type="number"
                  min="0"
                  max="5"
                  step="0.1"
                  value={filters.min_rating || ''}
                  onChange={(e) => updateFilter('min_rating', e.target.value ? parseFloat(e.target.value) : undefined)}
                  className="filter-input"
                  placeholder="0-5"
                />
              </div>
            </div>
          </div>

          {/* Website Status Filters */}
          <div className="filter-group">
            <h4 className="filter-group-title">Website Status</h4>
            <div className="filter-row">
              <select
                value={filters.website_status || ''}
                onChange={(e) => updateFilter('website_status', e.target.value || undefined)}
                className="filter-select"
              >
                <option value="">Any Status</option>
                <option value="none">None</option>
                <option value="generated">Generated</option>
                <option value="deployed">Deployed</option>
                <option value="sold">Sold</option>
              </select>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

