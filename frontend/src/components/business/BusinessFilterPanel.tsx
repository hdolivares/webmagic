import { useState, useEffect } from 'react'
import { api } from '@/services/api'
import './BusinessFilterPanel.css'

interface FilterPreset {
  id: string
  name: string
  filters: any
  is_public: boolean
  is_own: boolean
  created_at: string
}

interface QuickFilter {
  name: string
  filters: any
}

interface Props {
  onFilterApply: (filters: any) => void
  onFilterClear: () => void
  initialFilters?: any
}

export function BusinessFilterPanel({ onFilterApply, onFilterClear, initialFilters }: Props) {
  // Quick filters
  const [quickFilters, setQuickFilters] = useState<Record<string, QuickFilter>>({})
  
  // Saved presets
  const [presets, setPresets] = useState<FilterPreset[]>([])
  const [loadingPresets, setLoadingPresets] = useState(false)
  
  // Current filter state
  const [websiteStatus, setWebsiteStatus] = useState<string[]>([])
  const [state, setState] = useState('')
  const [city, setCity] = useState('')
  const [category, setCategory] = useState('')
  const [minRating, setMinRating] = useState<number | ''>('')
  const [minScore, setMinScore] = useState<number | ''>('')
  
  // UI state
  const [showPresets, setShowPresets] = useState(false)
  const [showSaveDialog, setShowSaveDialog] = useState(false)
  const [presetName, setPresetName] = useState('')
  const [presetIsPublic, setPresetIsPublic] = useState(false)
  
  // Active filters count
  const [activeFiltersCount, setActiveFiltersCount] = useState(0)

  useEffect(() => {
    loadQuickFilters()
    loadPresets()
  }, [])

  useEffect(() => {
    calculateActiveFilters()
  }, [websiteStatus, state, city, category, minRating, minScore])

  const loadQuickFilters = async () => {
    try {
      const data = await api.getQuickFilters()
      setQuickFilters(data.quick_filters)
    } catch (error) {
      console.error('Failed to load quick filters:', error)
    }
  }

  const loadPresets = async () => {
    try {
      setLoadingPresets(true)
      const data = await api.getFilterPresets()
      setPresets(data.presets)
    } catch (error) {
      console.error('Failed to load presets:', error)
    } finally {
      setLoadingPresets(false)
    }
  }

  const calculateActiveFilters = () => {
    let count = 0
    if (websiteStatus.length > 0) count++
    if (state) count++
    if (city) count++
    if (category) count++
    if (minRating !== '') count++
    if (minScore !== '') count++
    setActiveFiltersCount(count)
  }

  const buildFilters = () => {
    const conditions: any[] = []

    // Website status filter
    if (websiteStatus.length > 0) {
      if (websiteStatus.includes('none')) {
        conditions.push({
          OR: [
            { website_url: { operator: 'is_null', value: null } },
            { website_validation_status: { operator: 'in', value: ['missing', 'invalid'] } }
          ]
        })
      } else {
        conditions.push({
          website_validation_status: { operator: 'in', value: websiteStatus }
        })
      }
    }

    // Location filters
    if (state) {
      conditions.push({ state: { operator: 'eq', value: state } })
    }
    if (city) {
      conditions.push({ city: { operator: 'contains', value: city } })
    }

    // Category filter
    if (category) {
      conditions.push({ category: { operator: 'contains', value: category } })
    }

    // Rating filter
    if (minRating !== '') {
      conditions.push({ rating: { operator: 'gte', value: minRating } })
    }

    // Score filter
    if (minScore !== '') {
      conditions.push({ qualification_score: { operator: 'gte', value: minScore } })
    }

    // Combine with AND logic if multiple conditions
    if (conditions.length === 0) {
      return {}
    } else if (conditions.length === 1) {
      return conditions[0]
    } else {
      return { AND: conditions }
    }
  }

  const handleApplyFilters = () => {
    const filters = buildFilters()
    onFilterApply(filters)
  }

  const handleClearFilters = () => {
    setWebsiteStatus([])
    setState('')
    setCity('')
    setCategory('')
    setMinRating('')
    setMinScore('')
    onFilterClear()
  }

  const handleQuickFilter = (filterKey: string) => {
    const quickFilter = quickFilters[filterKey]
    if (quickFilter) {
      onFilterApply(quickFilter.filters)
    }
  }

  const handlePresetSelect = (preset: FilterPreset) => {
    onFilterApply(preset.filters)
    setShowPresets(false)
  }

  const handleSavePreset = async () => {
    if (!presetName.trim()) {
      alert('Please enter a preset name')
      return
    }

    try {
      const filters = buildFilters()
      await api.saveFilterPreset(presetName, filters, presetIsPublic)
      
      // Reload presets
      await loadPresets()
      
      // Reset dialog
      setPresetName('')
      setPresetIsPublic(false)
      setShowSaveDialog(false)
      
      alert('Filter preset saved successfully!')
    } catch (error) {
      console.error('Failed to save preset:', error)
      alert('Failed to save preset. Please try again.')
    }
  }

  const handleDeletePreset = async (presetId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    
    if (!confirm('Are you sure you want to delete this preset?')) {
      return
    }

    try {
      await api.deleteFilterPreset(presetId)
      await loadPresets()
    } catch (error) {
      console.error('Failed to delete preset:', error)
      alert('Failed to delete preset. Please try again.')
    }
  }

  const toggleWebsiteStatus = (status: string) => {
    setWebsiteStatus(prev => 
      prev.includes(status) 
        ? prev.filter(s => s !== status)
        : [...prev, status]
    )
  }

  return (
    <div className="filter-panel business-filter-panel">
      {/* Header */}
      <div className="filter-panel-header">
        <h3 className="filter-title">
          Filter Businesses
          {activeFiltersCount > 0 && (
            <span className="filter-count-badge">{activeFiltersCount}</span>
          )}
        </h3>
        <div className="filter-header-actions">
          <button
            className="filter-button filter-button-ghost"
            onClick={() => setShowPresets(!showPresets)}
          >
            📁 Saved Filters
          </button>
        </div>
      </div>

      {/* Quick Filters */}
      {Object.keys(quickFilters).length > 0 && (
        <div className="filter-section">
          <h4 className="filter-section-title">Quick Filters</h4>
          <div className="quick-filters-grid">
            {Object.entries(quickFilters).map(([key, filter]) => (
              <button
                key={key}
                className="quick-filter-button"
                onClick={() => handleQuickFilter(key)}
              >
                {filter.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Website Status Filter */}
      <div className="filter-section">
        <h4 className="filter-section-title">Website Status</h4>
        <div className="website-status-checkboxes">
          {[
            { value: 'none', label: 'No Website', color: 'amber' },
            { value: 'valid', label: 'Valid Website', color: 'green' },
            { value: 'invalid', label: 'Invalid Website', color: 'red' },
            { value: 'pending', label: 'Pending Validation', color: 'gray' }
          ].map(({ value, label, color }) => (
            <label key={value} className={`website-status-checkbox status-${color}`}>
              <input
                type="checkbox"
                checked={websiteStatus.includes(value)}
                onChange={() => toggleWebsiteStatus(value)}
              />
              <span className="checkbox-label">{label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Location Filters */}
      <div className="filter-section">
        <h4 className="filter-section-title">Location</h4>
        <div className="filter-form-group">
          <label className="filter-label">
            State
            <input
              type="text"
              className="filter-input"
              placeholder="e.g., CA, NY, TX"
              value={state}
              onChange={(e) => setState(e.target.value)}
            />
          </label>
        </div>
        <div className="filter-form-group">
          <label className="filter-label">
            City
            <input
              type="text"
              className="filter-input"
              placeholder="Search city..."
              value={city}
              onChange={(e) => setCity(e.target.value)}
            />
          </label>
        </div>
      </div>

      {/* Business Filters */}
      <div className="filter-section">
        <h4 className="filter-section-title">Business Details</h4>
        <div className="filter-form-group">
          <label className="filter-label">
            Category
            <input
              type="text"
              className="filter-input"
              placeholder="e.g., plumbers, dentists"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            />
          </label>
        </div>
        <div className="filter-form-row">
          <div className="filter-form-group">
            <label className="filter-label">
              Min Rating
              <input
                type="number"
                className="filter-input"
                placeholder="0-5"
                min="0"
                max="5"
                step="0.1"
                value={minRating}
                onChange={(e) => setMinRating(e.target.value ? parseFloat(e.target.value) : '')}
              />
            </label>
          </div>
          <div className="filter-form-group">
            <label className="filter-label">
              Min Score
              <input
                type="number"
                className="filter-input"
                placeholder="0-100"
                min="0"
                max="100"
                value={minScore}
                onChange={(e) => setMinScore(e.target.value ? parseInt(e.target.value) : '')}
              />
            </label>
          </div>
        </div>
      </div>

      {/* Active Filters */}
      {activeFiltersCount > 0 && (
        <div className="filter-section active-filters-section">
          <h4 className="filter-section-title">Active Filters ({activeFiltersCount})</h4>
          <div className="filter-chips-container">
            {websiteStatus.map(status => (
              <div key={status} className="filter-chip">
                Website: {status}
                <span className="filter-chip-close" onClick={() => toggleWebsiteStatus(status)}>
                  ×
                </span>
              </div>
            ))}
            {state && (
              <div className="filter-chip">
                State: {state}
                <span className="filter-chip-close" onClick={() => setState('')}>×</span>
              </div>
            )}
            {city && (
              <div className="filter-chip">
                City: {city}
                <span className="filter-chip-close" onClick={() => setCity('')}>×</span>
              </div>
            )}
            {category && (
              <div className="filter-chip">
                Category: {category}
                <span className="filter-chip-close" onClick={() => setCategory('')}>×</span>
              </div>
            )}
            {minRating !== '' && (
              <div className="filter-chip">
                Rating ≥ {minRating}
                <span className="filter-chip-close" onClick={() => setMinRating('')}>×</span>
              </div>
            )}
            {minScore !== '' && (
              <div className="filter-chip">
                Score ≥ {minScore}
                <span className="filter-chip-close" onClick={() => setMinScore('')}>×</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="filter-actions">
        <button
          className="filter-button filter-button-primary"
          onClick={handleApplyFilters}
          disabled={activeFiltersCount === 0}
        >
          Apply Filters
        </button>
        <button
          className="filter-button filter-button-secondary"
          onClick={handleClearFilters}
          disabled={activeFiltersCount === 0}
        >
          Clear All
        </button>
        <button
          className="filter-button filter-button-ghost"
          onClick={() => setShowSaveDialog(true)}
          disabled={activeFiltersCount === 0}
        >
          💾 Save Preset
        </button>
      </div>

      {/* Saved Presets Panel */}
      {showPresets && (
        <div className="presets-panel">
          <div className="presets-header">
            <h4 className="filter-section-title">Saved Filter Presets</h4>
            <button
              className="filter-button filter-button-ghost"
              onClick={() => setShowPresets(false)}
            >
              ✕
            </button>
          </div>
          
          {loadingPresets ? (
            <p className="presets-loading">Loading presets...</p>
          ) : presets.length === 0 ? (
            <p className="presets-empty">No saved presets yet. Create one by applying filters and clicking "Save Preset".</p>
          ) : (
            <div className="presets-grid">
              {presets.map(preset => (
                <div
                  key={preset.id}
                  className="filter-preset-card"
                  onClick={() => handlePresetSelect(preset)}
                >
                  <div className="filter-preset-header">
                    <h5 className="filter-preset-name">{preset.name}</h5>
                    {preset.is_public && (
                      <span className="filter-preset-badge">Public</span>
                    )}
                  </div>
                  <p className="filter-preset-description">
                    Created {new Date(preset.created_at).toLocaleDateString()}
                  </p>
                  {preset.is_own && (
                    <button
                      className="preset-delete-button"
                      onClick={(e) => handleDeletePreset(preset.id, e)}
                    >
                      🗑️
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Save Preset Dialog */}
      {showSaveDialog && (
        <div className="save-preset-dialog">
          <div className="dialog-header">
            <h4 className="filter-section-title">Save Filter Preset</h4>
            <button
              className="filter-button filter-button-ghost"
              onClick={() => setShowSaveDialog(false)}
            >
              ✕
            </button>
          </div>
          
          <div className="dialog-content">
            <div className="filter-form-group">
              <label className="filter-label">
                Preset Name
                <input
                  type="text"
                  className="filter-input"
                  placeholder="e.g., CA Businesses Without Websites"
                  value={presetName}
                  onChange={(e) => setPresetName(e.target.value)}
                  autoFocus
                />
              </label>
            </div>
            
            <label className="preset-public-checkbox">
              <input
                type="checkbox"
                checked={presetIsPublic}
                onChange={(e) => setPresetIsPublic(e.target.checked)}
              />
              <span>Make this preset available to all users</span>
            </label>
          </div>
          
          <div className="dialog-actions">
            <button
              className="filter-button filter-button-primary"
              onClick={handleSavePreset}
            >
              Save Preset
            </button>
            <button
              className="filter-button filter-button-secondary"
              onClick={() => setShowSaveDialog(false)}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

