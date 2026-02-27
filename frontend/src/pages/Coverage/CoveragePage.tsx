import { useState, useEffect, useMemo } from 'react'
import { Card } from '@/components/ui'
import { api } from '@/services/api'
import { US_CITIES_BY_STATE } from '@/data/cities'
import { IntelligentCampaignPanel } from '@/components/coverage/IntelligentCampaignPanel'
import '@/components/coverage/IntelligentCampaignPanel.css'

interface CampaignStats {
  // Grid-level (scraped rows)
  total_grids: number
  pending_grids: number
  in_progress_grids: number
  completed_grids: number
  failed_grids: number
  total_businesses_found: number
  total_locations: number
  total_categories: number
  completion_percentage: number
  estimated_cost: number
  actual_cost: number
  // Strategy (zone-plan) level — full planned scope
  total_strategies: number
  total_zones: number
  zones_completed: number
  zones_completion_pct: number
  strategy_cities: number
  strategy_categories: number
  available_categories: number
}

interface LocationCoverage {
  location: string
  state: string
  total_categories: number
  completed_categories: number
  pending_categories: number
  total_businesses: number
  completion_percentage: number
  last_scraped: string | null
}

interface CategoryCoverage {
  category: string
  total_locations: number
  completed_locations: number
  pending_locations: number
  total_businesses: number
  completion_percentage: number
  avg_businesses_per_location: number
}

export function CoveragePage() {
  const [stats, setStats] = useState<CampaignStats | null>(null)
  const [locations, setLocations] = useState<LocationCoverage[]>([])
  const [categories, setCategories] = useState<CategoryCoverage[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'overview' | 'locations' | 'categories'>('overview')
  
  
  // Scheduling settings
  const [scheduledSearches, setScheduledSearches] = useState(100)
  const [scheduleEnabled, setScheduleEnabled] = useState(false)
  const [batchMessage, setBatchMessage] = useState<string | null>(null)

  useEffect(() => {
    loadCampaignData()
  }, [])

  const loadCampaignData = async () => {
    try {
      const [statsData, locationsData, categoriesData] = await Promise.all([
        api.getCoverageStats(),
        api.getCoverageLocations({ limit: 50 }),
        api.getCoverageCategories({ limit: 20 }),
      ])
      
      setStats(statsData)
      setLocations(locationsData || [])
      setCategories(categoriesData || [])
      setLoading(false)
    } catch (error) {
      console.error('Failed to load campaign data:', error)
      setLoading(false)
    }
  }


  const startBatchScrape = async (priorityMin: number, limit: number) => {
    try {
      const response = await fetch(
        `/api/v1/coverage/campaigns/start-batch?priority_min=${priorityMin}&limit=${limit}`,
        { 
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
          }
        }
      )
      const data = await response.json()
      setBatchMessage(`Queued ${data.queued_tasks ?? 0} scraping tasks`)
      loadCampaignData()
    } catch (error) {
      setBatchMessage('Failed to start batch scrape')
    }
  }

  if (loading) {
    return <div className="loading-screen">Loading campaign data...</div>
  }

  // Full discoverable universe from the dropdown data (computed client-side)
  const totalAvailableCities = useMemo(
    () => Object.values(US_CITIES_BY_STATE).flat().length,
    []
  )
  const totalAvailableStates = useMemo(
    () => Object.keys(US_CITIES_BY_STATE).length,
    []
  )
  const availableCategories = stats?.available_categories || 0

  // Strategy-level progress (zones done vs zones planned)
  const hasStrategyData = (stats?.total_zones || 0) > 0
  const completionPct = hasStrategyData
    ? (stats?.zones_completion_pct || 0)
    : (stats?.completion_percentage || 0)
  const zonesCompleted = stats?.zones_completed || 0
  const totalZones = stats?.total_zones || 0

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Discovery Campaign</h1>
          <p className="page-description">
            {totalAvailableCities.toLocaleString()} cities across {totalAvailableStates} states · {availableCategories} business categories available
          </p>
        </div>
      </div>

      {/* Batch message toast */}
      {batchMessage && (
        <div className="coverage-toast" onClick={() => setBatchMessage(null)}>
          {batchMessage}
          <span className="coverage-toast-close">×</span>
        </div>
      )}

      {/* Stats Cards — three levels: universe → started → done */}
      <div className="stats-grid">

        {/* Level 1 — full discoverable universe */}
        <Card>
          <div className="stat-label">Available Universe</div>
          <div className="stat-value">{totalAvailableCities.toLocaleString()}</div>
          <div className="stat-meta">{totalAvailableStates} states · {totalAvailableCities.toLocaleString()} cities</div>
          <div className="stat-meta">{availableCategories} business categories</div>
        </Card>

        {/* Level 2 — how much has been started (active strategies) */}
        <Card>
          <div className="stat-label">Active Strategies</div>
          <div className="stat-value">{stats?.total_strategies?.toLocaleString() || '0'}</div>
          <div className="stat-meta">
            {stats?.strategy_cities || 0} {stats?.strategy_cities === 1 ? 'city' : 'cities'} × {stats?.strategy_categories || 0} categories
          </div>
          <div className="stat-meta">{totalZones.toLocaleString()} zones planned</div>
        </Card>

        {/* Level 3 — how much work is done */}
        <Card>
          <div className="stat-label">Zone Completion</div>
          <div className="stat-value">{completionPct.toFixed(1)}%</div>
          <div className="stat-meta">
            {zonesCompleted.toLocaleString()} of {totalZones.toLocaleString()} zones done
          </div>
          <div className="stat-meta">{(totalZones - zonesCompleted).toLocaleString()} remaining</div>
        </Card>

        <Card>
          <div className="stat-label">Businesses Found</div>
          <div className="stat-value text-success">
            {stats?.total_businesses_found?.toLocaleString() || '0'}
          </div>
          <div className="stat-meta">
            Actual cost: ${stats?.actual_cost?.toFixed(2) || '0.00'}
          </div>
          <div className="stat-meta">of ${stats?.estimated_cost?.toFixed(2) || '0.00'} estimated</div>
        </Card>

      </div>

      {/* Overall Progress Bar */}
      <Card>
        <div className="card-header">
          <h2 className="card-title">Overall Progress</h2>
          <div className="coverage-status-pills">
            <span className="status-pill status-pill--success">{zonesCompleted.toLocaleString()} zones done</span>
            <span className="status-pill status-pill--secondary">{(totalZones - zonesCompleted).toLocaleString()} remaining</span>
            <span className="status-pill status-pill--info">{stats?.total_strategies || 0} strategies · {stats?.strategy_cities || 0} {stats?.strategy_cities === 1 ? 'city' : 'cities'} · {stats?.strategy_categories || 0} categories</span>
          </div>
        </div>
        <div className="progress-bar-wrapper">
          <div
            className="progress-bar"
            style={{ width: `${completionPct}%` }}
          />
        </div>
        <div className="progress-bar-label">
          {completionPct.toFixed(1)}% of active strategies complete
          <span className="progress-bar-label-sub"> · {zonesCompleted.toLocaleString()} of {totalZones.toLocaleString()} zones scraped</span>
        </div>
      </Card>

      {/* Intelligent Campaign Panel - Claude-powered with Draft Mode */}
      <IntelligentCampaignPanel onCampaignUpdate={loadCampaignData} />

      {/* Tabs */}
      <div className="tabs-container">
        <div className="tabs">
          <button
            onClick={() => setActiveTab('overview')}
            className={`tab ${activeTab === 'overview' ? 'tab-active' : ''}`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('locations')}
            className={`tab ${activeTab === 'locations' ? 'tab-active' : ''}`}
          >
            Locations ({locations.length})
          </button>
          <button
            onClick={() => setActiveTab('categories')}
            className={`tab ${activeTab === 'categories' ? 'tab-active' : ''}`}
          >
            Categories ({categories.length})
          </button>
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'locations' && (
        <Card>
          <div className="card-header">
            <h2 className="card-title">Coverage by Location</h2>
          </div>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th className="text-left">Location</th>
                  <th className="text-center">Categories</th>
                  <th className="text-center">Completed</th>
                  <th className="text-center">Businesses</th>
                  <th className="text-center">Progress</th>
                </tr>
              </thead>
              <tbody>
                {locations.map((loc) => (
                  <tr key={loc.location}>
                    <td>
                      <div className="font-semibold">{loc.location}</div>
                      <div className="text-secondary">{loc.state}</div>
                    </td>
                    <td className="text-center">{loc.total_categories}</td>
                    <td className="text-center text-success">
                      {loc.completed_categories || 0}
                    </td>
                    <td className="text-center font-bold">
                      {loc.total_businesses?.toLocaleString() || '0'}
                    </td>
                    <td className="text-center">
                      <div className="progress-inline">
                        <div className="progress-bar-small">
                          <div
                            className="progress-fill"
                            style={{ width: `${loc.completion_percentage || 0}%` }}
                          />
                        </div>
                        <span className="progress-text">{loc.completion_percentage?.toFixed(0) || '0'}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {activeTab === 'categories' && (
        <Card>
          <div className="card-header">
            <h2 className="card-title">Coverage by Category</h2>
          </div>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th className="text-left">Category</th>
                  <th className="text-center">Locations</th>
                  <th className="text-center">Completed</th>
                  <th className="text-center">Avg/Location</th>
                  <th className="text-center">Total Businesses</th>
                  <th className="text-center">Progress</th>
                </tr>
              </thead>
              <tbody>
                {categories.map((cat) => (
                  <tr key={cat.category}>
                    <td className="font-semibold capitalize">{cat.category}</td>
                    <td className="text-center">{cat.total_locations || 0}</td>
                    <td className="text-center text-success">
                      {cat.completed_locations || 0}
                    </td>
                    <td className="text-center">{cat.avg_businesses_per_location?.toFixed(1) || '0.0'}</td>
                    <td className="text-center font-bold">
                      {cat.total_businesses?.toLocaleString() || '0'}
                    </td>
                    <td className="text-center">
                      <div className="progress-inline">
                        <div className="progress-bar-small">
                          <div
                            className="progress-fill"
                            style={{ width: `${cat.completion_percentage || 0}%` }}
                          />
                        </div>
                        <span className="progress-text">{cat.completion_percentage?.toFixed(0) || '0'}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Automated Scheduling */}
      <Card>
        <div className="card-header">
          <h2 className="card-title">Automated Scheduling</h2>
        </div>
        <div className="form-section">
          <div className="form-row">
            <div>
              <div className="form-label">Enable Automated Discovery</div>
              <div className="form-hint">
                Automatically queue searches daily based on priority
              </div>
            </div>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={scheduleEnabled}
                onChange={(e) => setScheduleEnabled(e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </div>
          
          {scheduleEnabled && (
            <div className="form-section-nested">
              <div className="form-group">
                <label className="form-label">
                  Searches Per Day
                </label>
                <input
                  type="number"
                  value={scheduledSearches}
                  onChange={(e) => setScheduledSearches(parseInt(e.target.value))}
                  min="10"
                  max="1000"
                  step="10"
                  className="input input-number"
                />
                <div className="form-hint">
                  Est. cost: ${(scheduledSearches * 0.50).toFixed(2)}/day
                </div>
              </div>

              <button className="btn btn-primary">
                Save Schedule Settings
              </button>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}
