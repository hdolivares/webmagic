import { useEffect, useState } from 'react'
import { api } from '@/services/api'
import './ZoneStatisticsCard.css'

interface ZoneStatistics {
  zone_id: string
  coverage_id: string
  status: string
  total_businesses: number
  qualified_leads: number
  with_websites: number
  without_websites: number
  invalid_websites: number
  websites_generated: number
  generation_in_progress: number
  generation_pending: number
  last_scraped_at: string | null
  last_scrape_details: any
  avg_rating: number | null
  avg_qualification_score: number | null
  qualification_rate: number | null
  website_coverage_rate: number | null
  raw_data: {
    lead_count: number
    last_scrape_size: number
    scrape_count: number
  }
}

interface Props {
  zoneId: string
  autoLoad?: boolean
  onGenerateWebsites?: (pendingCount: number) => void
}

export function ZoneStatisticsCard({ zoneId, autoLoad = false, onGenerateWebsites }: Props) {
  const [stats, setStats] = useState<ZoneStatistics | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadStatistics = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await api.getZoneStatistics(zoneId)
      setStats(data)
    } catch (err: any) {
      console.error('Failed to load zone statistics:', err)
      setError(err.response?.data?.detail || 'Failed to load statistics')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (autoLoad) {
      loadStatistics()
    }
  }, [zoneId, autoLoad])

  const handleGenerateClick = () => {
    if (stats && onGenerateWebsites) {
      onGenerateWebsites(stats.generation_pending)
    }
  }

  if (loading) {
    return (
      <div className="coverage-card zone-stats-loading">
        <div className="loading-spinner"></div>
        <p>Loading zone statistics...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="coverage-card zone-stats-error">
        <p className="error-message">{error}</p>
        <button className="coverage-button-secondary" onClick={loadStatistics}>
          Retry
        </button>
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="coverage-card zone-stats-empty">
        <p>No statistics available for this zone</p>
        <button className="coverage-button-secondary" onClick={loadStatistics}>
          Load Statistics
        </button>
      </div>
    )
  }

  return (
    <div className="coverage-card zone-statistics-card">
      {/* Header */}
      <div className="coverage-card-header">
        <div>
          <h3 className="coverage-card-title">{stats.zone_id}</h3>
          {stats.last_scraped_at && (
            <p className="zone-last-scraped">
              Last scraped: {new Date(stats.last_scraped_at).toLocaleString()}
            </p>
          )}
        </div>
        <span className={`coverage-status-badge ${stats.status}`}>
          {stats.status}
        </span>
      </div>

      {/* Main Metrics Grid */}
      <div className="coverage-metrics-grid">
        <div className="coverage-metric-card">
          <p className="coverage-metric-value">{stats.total_businesses}</p>
          <p className="coverage-metric-label">Total Businesses</p>
        </div>

        <div className="coverage-metric-card">
          <p className="coverage-metric-value">{stats.qualified_leads}</p>
          <p className="coverage-metric-label">Qualified Leads</p>
        </div>

        {stats.qualification_rate !== null && (
          <div className="coverage-metric-card">
            <p className="coverage-metric-value">{stats.qualification_rate}%</p>
            <p className="coverage-metric-label">Qualification Rate</p>
          </div>
        )}

        {stats.avg_rating !== null && (
          <div className="coverage-metric-card">
            <p className="coverage-metric-value">{stats.avg_rating.toFixed(1)}</p>
            <p className="coverage-metric-label">Avg Rating</p>
          </div>
        )}
      </div>

      {/* Website Breakdown */}
      <div className="zone-website-breakdown">
        <h4 className="breakdown-title">Website Status Breakdown</h4>
        
        <div className="website-metrics">
          <div className="website-metric-row metric-website-valid">
            <div className="metric-info">
              <span className="metric-value">{stats.with_websites}</span>
              <span className="metric-label">With Valid Websites</span>
            </div>
            {stats.total_businesses > 0 && (
              <span className="metric-percentage">
                {((stats.with_websites / stats.total_businesses) * 100).toFixed(1)}%
              </span>
            )}
          </div>

          <div className="website-metric-row metric-website-none">
            <div className="metric-info">
              <span className="metric-value">{stats.without_websites}</span>
              <span className="metric-label">Without Websites</span>
            </div>
            {stats.total_businesses > 0 && (
              <span className="metric-percentage">
                {((stats.without_websites / stats.total_businesses) * 100).toFixed(1)}%
              </span>
            )}
          </div>

          <div className="website-metric-row metric-website-invalid">
            <div className="metric-info">
              <span className="metric-value">{stats.invalid_websites}</span>
              <span className="metric-label">Invalid Websites</span>
            </div>
            {stats.total_businesses > 0 && (
              <span className="metric-percentage">
                {((stats.invalid_websites / stats.total_businesses) * 100).toFixed(1)}%
              </span>
            )}
          </div>

          <div className="website-metric-row metric-website-generated">
            <div className="metric-info">
              <span className="metric-value">{stats.websites_generated}</span>
              <span className="metric-label">Websites Generated</span>
            </div>
            {stats.without_websites > 0 && (
              <span className="metric-percentage">
                {((stats.websites_generated / stats.without_websites) * 100).toFixed(1)}%
              </span>
            )}
          </div>

          {stats.generation_in_progress > 0 && (
            <div className="website-metric-row metric-website-generating">
              <div className="metric-info">
                <span className="metric-value">{stats.generation_in_progress}</span>
                <span className="metric-label">Generation In Progress</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Website Coverage Progress */}
      {stats.website_coverage_rate !== null && (
        <div className="coverage-progress">
          <div className="coverage-progress-label">
            <span>Website Coverage</span>
            <span className="progress-percentage">{stats.website_coverage_rate}%</span>
          </div>
          <div className="coverage-progress-bar">
            <div 
              className="coverage-progress-fill" 
              style={{ width: `${stats.website_coverage_rate}%` }}
            />
          </div>
          <p className="coverage-progress-description">
            {stats.with_websites + stats.websites_generated} of {stats.total_businesses} businesses have websites
          </p>
        </div>
      )}

      {/* Action Button */}
      {stats.generation_pending > 0 && onGenerateWebsites && (
        <div className="zone-actions">
          <button 
            className="coverage-button coverage-button-primary"
            onClick={handleGenerateClick}
          >
            Generate {stats.generation_pending} Website{stats.generation_pending !== 1 ? 's' : ''}
          </button>
        </div>
      )}

      {/* Last Scrape Details (if available) */}
      {stats.last_scrape_details && (
        <details className="zone-scrape-details">
          <summary className="details-summary">Last Scrape Details</summary>
          <div className="details-content">
            <div className="detail-row">
              <span className="detail-label">Raw Businesses:</span>
              <span className="detail-value">{stats.last_scrape_details.raw_businesses || 0}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Qualified Leads:</span>
              <span className="detail-value">{stats.last_scrape_details.qualified_leads || 0}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">New Businesses:</span>
              <span className="detail-value">{stats.last_scrape_details.new_businesses || 0}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">With Websites:</span>
              <span className="detail-value">{stats.last_scrape_details.with_websites || 0}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Without Websites:</span>
              <span className="detail-value">{stats.last_scrape_details.without_websites || 0}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Queued for Generation:</span>
              <span className="detail-value">{stats.last_scrape_details.queued_for_generation || 0}</span>
            </div>
            {stats.last_scrape_details.timestamp && (
              <div className="detail-row">
                <span className="detail-label">Timestamp:</span>
                <span className="detail-value">
                  {new Date(stats.last_scrape_details.timestamp).toLocaleString()}
                </span>
              </div>
            )}
          </div>
        </details>
      )}
    </div>
  )
}

