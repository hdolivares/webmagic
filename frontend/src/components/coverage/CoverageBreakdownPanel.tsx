import { useEffect, useState } from 'react'
import { api } from '@/services/api'
import { ZoneStatisticsCard } from './ZoneStatisticsCard'
import './CoverageBreakdownPanel.css'

interface StrategyOverview {
  strategy_id: string
  city: string
  state: string
  category: string
  status: boolean
  zones: {
    total: number
    completed: number
    in_progress: number
    pending: number
  }
  businesses: {
    total: number
    qualified: number
    with_websites: number
    without_websites: number
    websites_generated: number
    generation_in_progress: number
    generation_pending: number
  }
  performance: {
    avg_businesses_per_zone: number
    completion_rate: number
    qualification_rate: number
    website_coverage_rate: number
  }
  zone_details: Array<{
    zone_id: string
    status: string
    total_businesses: number
    with_websites: number
    without_websites: number
    websites_generated: number
  }>
}

interface Props {
  strategyId: string
  autoLoad?: boolean
  showZoneDetails?: boolean
}

export function CoverageBreakdownPanel({ 
  strategyId, 
  autoLoad = false,
  showZoneDetails = true 
}: Props) {
  const [overview, setOverview] = useState<StrategyOverview | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedZones, setExpandedZones] = useState<Set<string>>(new Set())

  const loadOverview = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await api.get(`/intelligent-campaigns/strategies/${strategyId}/overview`)
      setOverview(response.data)
    } catch (err: any) {
      console.error('Failed to load strategy overview:', err)
      setError(err.response?.data?.detail || 'Failed to load overview')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (autoLoad) {
      loadOverview()
    }
  }, [strategyId, autoLoad])

  const toggleZoneExpansion = (zoneId: string) => {
    setExpandedZones(prev => {
      const newSet = new Set(prev)
      if (newSet.has(zoneId)) {
        newSet.delete(zoneId)
      } else {
        newSet.add(zoneId)
      }
      return newSet
    })
  }

  if (loading) {
    return (
      <div className="coverage-card breakdown-loading">
        <div className="loading-spinner"></div>
        <p>Loading coverage breakdown...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="coverage-card breakdown-error">
        <p className="error-message">{error}</p>
        <button className="coverage-button-secondary" onClick={loadOverview}>
          Retry
        </button>
      </div>
    )
  }

  if (!overview) {
    return (
      <div className="coverage-card breakdown-empty">
        <p>No overview data available</p>
        <button className="coverage-button-secondary" onClick={loadOverview}>
          Load Overview
        </button>
      </div>
    )
  }

  return (
    <div className="coverage-breakdown-panel">
      {/* Strategy Header */}
      <div className="coverage-card breakdown-header">
        <div className="header-content">
          <h2 className="coverage-card-title">
            {overview.city}, {overview.state} - {overview.category}
          </h2>
          <p className="strategy-subtitle">
            Strategy ID: {overview.strategy_id.substring(0, 8)}...
          </p>
        </div>
        <span className={`coverage-status-badge ${overview.status ? 'in-progress' : 'completed'}`}>
          {overview.status ? 'Active' : 'Completed'}
        </span>
      </div>

      {/* Main Metrics Overview */}
      <div className="coverage-card breakdown-metrics">
        <h3 className="section-title">Overall Performance</h3>
        
        {/* Zone Progress */}
        <div className="metric-section">
          <h4 className="metric-section-title">Zone Coverage</h4>
          <div className="coverage-metrics-grid">
            <div className="coverage-metric-card">
              <p className="coverage-metric-value">{overview.zones.completed}</p>
              <p className="coverage-metric-label">Completed</p>
            </div>
            <div className="coverage-metric-card">
              <p className="coverage-metric-value">{overview.zones.in_progress}</p>
              <p className="coverage-metric-label">In Progress</p>
            </div>
            <div className="coverage-metric-card">
              <p className="coverage-metric-value">{overview.zones.pending}</p>
              <p className="coverage-metric-label">Pending</p>
            </div>
            <div className="coverage-metric-card">
              <p className="coverage-metric-value">{overview.zones.total}</p>
              <p className="coverage-metric-label">Total Zones</p>
            </div>
          </div>

          <div className="coverage-progress">
            <div className="coverage-progress-label">
              <span>Zone Completion</span>
              <span className="progress-percentage">{overview.performance.completion_rate}%</span>
            </div>
            <div className="coverage-progress-bar">
              <div 
                className="coverage-progress-fill" 
                style={{ width: `${overview.performance.completion_rate}%` }}
              />
            </div>
          </div>
        </div>

        {/* Business Metrics */}
        <div className="metric-section">
          <h4 className="metric-section-title">Business Metrics</h4>
          <div className="coverage-metrics-grid">
            <div className="coverage-metric-card">
              <p className="coverage-metric-value">{overview.businesses.total}</p>
              <p className="coverage-metric-label">Total Businesses</p>
            </div>
            <div className="coverage-metric-card">
              <p className="coverage-metric-value">{overview.businesses.qualified}</p>
              <p className="coverage-metric-label">Qualified Leads</p>
            </div>
            <div className="coverage-metric-card">
              <p className="coverage-metric-value">{overview.performance.qualification_rate}%</p>
              <p className="coverage-metric-label">Qualification Rate</p>
            </div>
            <div className="coverage-metric-card">
              <p className="coverage-metric-value">{overview.performance.avg_businesses_per_zone}</p>
              <p className="coverage-metric-label">Avg Per Zone</p>
            </div>
          </div>
        </div>

        {/* Website Status Metrics */}
        <div className="metric-section">
          <h4 className="metric-section-title">Website Status Overview</h4>
          
          <div className="website-status-grid">
            <div className="website-status-card metric-website-valid">
              <div className="status-card-content">
                <div className="status-icon">✓</div>
                <div className="status-info">
                  <p className="status-value">{overview.businesses.with_websites}</p>
                  <p className="status-label">With Valid Websites</p>
                </div>
              </div>
              <div className="status-percentage">
                {overview.businesses.total > 0 
                  ? ((overview.businesses.with_websites / overview.businesses.total) * 100).toFixed(1)
                  : 0}%
              </div>
            </div>

            <div className="website-status-card metric-website-none">
              <div className="status-card-content">
                <div className="status-icon">⚠</div>
                <div className="status-info">
                  <p className="status-value">{overview.businesses.without_websites}</p>
                  <p className="status-label">Without Websites</p>
                </div>
              </div>
              <div className="status-percentage">
                {overview.businesses.total > 0 
                  ? ((overview.businesses.without_websites / overview.businesses.total) * 100).toFixed(1)
                  : 0}%
              </div>
            </div>

            <div className="website-status-card metric-website-generated">
              <div className="status-card-content">
                <div className="status-icon">★</div>
                <div className="status-info">
                  <p className="status-value">{overview.businesses.websites_generated}</p>
                  <p className="status-label">Websites Generated</p>
                </div>
              </div>
              <div className="status-percentage">
                {overview.businesses.without_websites > 0 
                  ? ((overview.businesses.websites_generated / overview.businesses.without_websites) * 100).toFixed(1)
                  : 0}%
              </div>
            </div>

            <div className="website-status-card metric-website-generating">
              <div className="status-card-content">
                <div className="status-icon">⟳</div>
                <div className="status-info">
                  <p className="status-value">{overview.businesses.generation_in_progress}</p>
                  <p className="status-label">Generation In Progress</p>
                </div>
              </div>
            </div>
          </div>

          {/* Website Coverage Progress */}
          <div className="coverage-progress">
            <div className="coverage-progress-label">
              <span>Website Coverage</span>
              <span className="progress-percentage">{overview.performance.website_coverage_rate}%</span>
            </div>
            <div className="coverage-progress-bar">
              <div 
                className="coverage-progress-fill" 
                style={{ width: `${overview.performance.website_coverage_rate}%` }}
              />
            </div>
            <p className="coverage-progress-description">
              {overview.businesses.with_websites + overview.businesses.websites_generated} of {overview.businesses.total} businesses have websites
            </p>
          </div>

          {/* Generation Action */}
          {overview.businesses.generation_pending > 0 && (
            <div className="generation-action">
              <button className="coverage-button coverage-button-primary">
                Queue {overview.businesses.generation_pending} Business{overview.businesses.generation_pending !== 1 ? 'es' : ''} for Website Generation
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Per-Zone Details */}
      {showZoneDetails && overview.zone_details && overview.zone_details.length > 0 && (
        <div className="coverage-card zone-details-section">
          <h3 className="section-title">
            Per-Zone Breakdown
            <span className="zone-count">({overview.zone_details.length} zones)</span>
          </h3>
          
          <div className="zone-details-list">
            {overview.zone_details.map((zone) => (
              <div key={zone.zone_id} className="zone-detail-item">
                <button
                  className="zone-detail-header"
                  onClick={() => toggleZoneExpansion(zone.zone_id)}
                >
                  <div className="zone-header-left">
                    <span className="zone-id">{zone.zone_id}</span>
                    <span className={`coverage-status-badge ${zone.status}`}>
                      {zone.status}
                    </span>
                  </div>
                  <div className="zone-header-right">
                    <span className="zone-quick-stats">
                      {zone.total_businesses} businesses · 
                      {zone.with_websites} with sites · 
                      {zone.websites_generated} generated
                    </span>
                    <span className="expand-icon">
                      {expandedZones.has(zone.zone_id) ? '▼' : '▶'}
                    </span>
                  </div>
                </button>

                {expandedZones.has(zone.zone_id) && (
                  <div className="zone-detail-content">
                    <ZoneStatisticsCard 
                      zoneId={zone.zone_id}
                      autoLoad={true}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

