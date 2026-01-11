/**
 * Coverage Campaign Management Page
 * 
 * Displays campaign progress, location/category coverage,
 * and controls for starting/scheduling automated discovery.
 */
import { useState, useEffect } from 'react'
import { Card } from '@/components/ui/card'
import { api } from '@/services/api'

interface CampaignStats {
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

  useEffect(() => {
    loadCampaignData()
  }, [])

  const loadCampaignData = async () => {
    try {
      const [statsData, locationsData, categoriesData] = await Promise.all([
        fetch('/api/v1/coverage/campaigns/stats').then(r => r.json()),
        fetch('/api/v1/coverage/campaigns/locations?limit=50').then(r => r.json()),
        fetch('/api/v1/coverage/campaigns/categories?limit=20').then(r => r.json()),
      ])
      
      setStats(statsData)
      setLocations(locationsData)
      setCategories(categoriesData)
      setLoading(false)
    } catch (error) {
      console.error('Failed to load campaign data:', error)
      setLoading(false)
    }
  }

  const startBatchScrape = async (priorityMin: number, limit: number) => {
    if (!confirm(`Start scraping ${limit} high-priority grids?`)) return
    
    try {
      const response = await fetch(
        `/api/v1/coverage/campaigns/start-batch?priority_min=${priorityMin}&limit=${limit}`,
        { method: 'POST' }
      )
      const data = await response.json()
      alert(`Success! Queued ${data.queued_tasks} scraping tasks`)
      loadCampaignData()
    } catch (error) {
      alert('Failed to start batch scrape: ' + error)
    }
  }

  if (loading) {
    return <div className="loading-screen">Loading campaign data...</div>
  }

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Discovery Campaign</h1>
          <p className="page-description">
            Systematic business discovery across 346 US cities
          </p>
        </div>
        
        {/* Quick Actions */}
        <div className="btn-group">
          <button
            onClick={() => startBatchScrape(9, 50)}
            className="btn btn-primary"
          >
            Start 50 High-Priority
          </button>
          <button
            onClick={() => startBatchScrape(7, 100)}
            className="btn btn-secondary"
          >
            Start 100 Medium-Priority
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="stats-grid">
        <Card>
          <div className="stat-label">Total Grids</div>
          <div className="stat-value">{stats?.total_grids.toLocaleString()}</div>
          <div className="stat-meta">
            {stats?.total_locations} cities × {stats?.total_categories} categories
          </div>
        </Card>

        <Card>
          <div className="stat-label">Completion</div>
          <div className="stat-value">{stats?.completion_percentage.toFixed(1)}%</div>
          <div className="stat-meta">
            {stats?.completed_grids} of {stats?.total_grids} complete
          </div>
        </Card>

        <Card>
          <div className="stat-label">Businesses Found</div>
          <div className="stat-value text-success">
            {stats?.total_businesses_found.toLocaleString()}
          </div>
          <div className="stat-meta">
            {stats?.pending_grids} searches pending
          </div>
        </Card>

        <Card>
          <div className="stat-label">Cost</div>
          <div className="stat-value">${stats?.actual_cost.toFixed(2)}</div>
          <div className="stat-meta">
            of ${stats?.estimated_cost.toFixed(2)} estimated
          </div>
        </Card>
      </div>

      {/* Progress Bar */}
      <Card>
        <div className="card-header">
          <h2 className="card-title">Overall Progress</h2>
        </div>
        <div className="progress-bar-wrapper">
          <div
            className="progress-bar"
            style={{ width: `${stats?.completion_percentage}%` }}
          >
            {stats?.completion_percentage.toFixed(1)}%
          </div>
        </div>
        <div className="progress-labels">
          <span className="text-success">{stats?.completed_grids} Completed</span>
          <span className="text-info">{stats?.in_progress_grids} In Progress</span>
          <span className="text-secondary">{stats?.pending_grids} Pending</span>
          <span className="text-error">{stats?.failed_grids} Failed</span>
        </div>
      </Card>

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
                      {loc.completed_categories}
                    </td>
                    <td className="text-center font-bold">
                      {loc.total_businesses.toLocaleString()}
                    </td>
                    <td className="text-center">
                      <div className="progress-inline">
                        <div className="progress-bar-small">
                          <div
                            className="progress-fill"
                            style={{ width: `${loc.completion_percentage}%` }}
                          />
                        </div>
                        <span className="progress-text">{loc.completion_percentage.toFixed(0)}%</span>
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
                    <td className="text-center">{cat.total_locations}</td>
                    <td className="text-center text-success">
                      {cat.completed_locations}
                    </td>
                    <td className="text-center">{cat.avg_businesses_per_location.toFixed(1)}</td>
                    <td className="text-center font-bold">
                      {cat.total_businesses.toLocaleString()}
                    </td>
                    <td className="text-center">
                      <div className="progress-inline">
                        <div className="progress-bar-small">
                          <div
                            className="progress-fill"
                            style={{ width: `${cat.completion_percentage}%` }}
                          />
                        </div>
                        <span className="progress-text">{cat.completion_percentage.toFixed(0)}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}
