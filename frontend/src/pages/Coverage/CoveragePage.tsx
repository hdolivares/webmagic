/**
 * Coverage Campaign Management Page
 * 
 * Displays campaign progress, location/category coverage,
 * and controls for starting/scheduling automated discovery.
 */
import { useState, useEffect } from 'react'
import { Card } from '@/components/ui'
import { api } from '@/services/api'
import { IntelligentCampaignPanel } from '@/components/coverage/IntelligentCampaignPanel'
import '@/components/coverage/IntelligentCampaignPanel.css'

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
  
  // Manual testing
  const [testSearchCount, setTestSearchCount] = useState(5)
  const [testRunning, setTestRunning] = useState(false)
  const [testResults, setTestResults] = useState<any>(null)
  
  // Scheduling settings
  const [scheduledSearches, setScheduledSearches] = useState(100)
  const [scheduleEnabled, setScheduleEnabled] = useState(false)

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

  const runTestSearches = async () => {
    if (!confirm(`Run ${testSearchCount} test searches? This will scrape real businesses and use API credits.`)) return
    
    setTestRunning(true)
    setTestResults(null)
    
    try {
      const response = await fetch(
        `/api/v1/coverage/campaigns/test-searches?count=${testSearchCount}&priority_min=7`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
          },
        }
      )
      
      if (response.ok) {
        const data = await response.json()
        setTestResults(data)
        alert(`✅ Completed ${data.searches_completed}/${data.total_requested} searches successfully!`)
        loadCampaignData() // Refresh stats
      } else {
        const error = await response.json()
        alert(`Failed: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Error running test searches:', error)
      alert('Error running test searches: ' + error)
    } finally {
      setTestRunning(false)
    }
  }

  const startBatchScrape = async (priorityMin: number, limit: number) => {
    if (!confirm(`Start scraping ${limit} high-priority grids?`)) return
    
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
          <div className="stat-value">{stats?.total_grids?.toLocaleString() || '0'}</div>
          <div className="stat-meta">
            {stats?.total_locations || 0} cities × {stats?.total_categories || 0} categories
          </div>
        </Card>

        <Card>
          <div className="stat-label">Completion</div>
          <div className="stat-value">{stats?.completion_percentage?.toFixed(1) || '0'}%</div>
          <div className="stat-meta">
            {stats?.completed_grids} of {stats?.total_grids} complete
          </div>
        </Card>

        <Card>
          <div className="stat-label">Businesses Found</div>
          <div className="stat-value text-success">
            {stats?.total_businesses_found?.toLocaleString() || '0'}
          </div>
          <div className="stat-meta">
            {stats?.pending_grids || 0} searches pending
          </div>
        </Card>

        <Card>
          <div className="stat-label">Cost</div>
          <div className="stat-value">${stats?.actual_cost?.toFixed(2) || '0.00'}</div>
          <div className="stat-meta">
            of ${stats?.estimated_cost?.toFixed(2) || '0.00'} estimated
          </div>
        </Card>
      </div>

      {/* Intelligent Campaign Panel - Claude-powered */}
      <IntelligentCampaignPanel />

      {/* Quick Validation Section - Simplified */}
      <Card>
        <details className="validation-section">
          <summary className="card-header" style={{ cursor: 'pointer' }}>
            <h2 className="card-title">🔍 Quick Validation (Optional)</h2>
            <p className="text-sm text-secondary">Spot-check the system with a few test searches</p>
          </summary>
          <div className="card-body space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Test Controls */}
            <div className="space-y-4">
              <div>
                <label className="form-label flex items-center justify-between">
                  <span>Number of Searches</span>
                  <span className="badge badge-primary">{testSearchCount}</span>
                </label>
                <input
                  type="range"
                  min="1"
                  max="25"
                  value={testSearchCount}
                  onChange={(e) => setTestSearchCount(parseInt(e.target.value))}
                  className="w-full"
                  disabled={testRunning}
                />
                <div className="flex justify-between text-xs text-secondary mt-1">
                  <span>1</span>
                  <span>25</span>
                </div>
              </div>

              <div className="test-buttons" style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  onClick={() => { setTestSearchCount(5); runTestSearches(); }}
                  disabled={testRunning}
                  className="btn btn-secondary"
                >
                  Test 5 Searches
                </button>
                <button
                  onClick={() => { setTestSearchCount(10); runTestSearches(); }}
                  disabled={testRunning}
                  className="btn btn-secondary"
                >
                  Test 10 Searches
                </button>
                <button
                  onClick={() => { setTestSearchCount(25); runTestSearches(); }}
                  disabled={testRunning}
                  className="btn btn-secondary"
                >
                  Test 25 Searches
                </button>
              </div>

              {testRunning && (
                <div className="alert alert-info text-sm">
                  <span className="spinner-sm"></span>
                  Running {testSearchCount} test searches...
                </div>
              )}

              <div className="alert alert-info text-sm">
                <p><strong>Quick validation:</strong> Tests {testSearchCount} high-priority locations to verify the system is working. Cost: ~${(testSearchCount * 0.50).toFixed(2)}</p>
              </div>
            </div>

            {/* Test Results */}
            <div>
              <h3 className="font-semibold mb-3">Last Test Results</h3>
              {!testResults ? (
                <div className="text-center py-8 text-secondary">
                  <p>No test results yet.</p>
                  <p className="text-sm mt-2">Run a test to see results here.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="stats-grid grid-cols-2">
                    <div className="stat-card bg-success/10">
                      <div className="stat-label">Successful</div>
                      <div className="stat-value text-success">{testResults.searches_completed}</div>
                    </div>
                    <div className="stat-card bg-error/10">
                      <div className="stat-label">Failed</div>
                      <div className="stat-value text-error">{testResults.searches_failed}</div>
                    </div>
                  </div>

                  <div className="max-h-64 overflow-y-auto space-y-2">
                    {testResults.results?.map((result: any, index: number) => (
                      <div
                        key={index}
                        className={`p-3 rounded-lg border ${
                          result.status === 'success'
                            ? 'border-success bg-success/5'
                            : 'border-error bg-error/5'
                        }`}
                      >
                        <div className="font-semibold">{result.location}</div>
                        <div className="text-sm text-secondary">{result.industry}</div>
                        {result.status === 'success' ? (
                          <div className="text-sm mt-2">
                            Found: <strong>{result.businesses_found}</strong> | 
                            Qualified: <strong>{result.qualified}</strong> | 
                            Rate: <strong>{result.qualification_rate?.toFixed(1)}%</strong>
                          </div>
                        ) : (
                          <div className="text-sm text-error mt-2">{result.error}</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </details>
      </Card>

      {/* Progress Bar */}
      <Card>
        <div className="card-header">
          <h2 className="card-title">Overall Progress</h2>
        </div>
        <div className="progress-bar-wrapper">
          <div
            className="progress-bar"
            style={{ width: `${stats?.completion_percentage || 0}%` }}
          >
            {stats?.completion_percentage?.toFixed(1) || '0'}%
          </div>
        </div>
        <div className="progress-labels">
          <span className="text-success">{stats?.completed_grids || 0} Completed</span>
          <span className="text-info">{stats?.in_progress_grids || 0} In Progress</span>
          <span className="text-secondary">{stats?.pending_grids || 0} Pending</span>
          <span className="text-error">{stats?.failed_grids || 0} Failed</span>
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
    </div>
  )
}
