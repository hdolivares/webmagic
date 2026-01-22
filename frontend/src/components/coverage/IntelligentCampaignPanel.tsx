import { useState } from 'react'
import { Card, Input, Button, Select, SelectItem, Spinner } from '@/components/ui'
import { api } from '@/services/api'
import './IntelligentCampaignPanel.css'

interface Zone {
  zone_id: string
  lat: number
  lon: number
  radius_km: number
  priority: string
  reason?: string
  estimated_businesses?: number
  area_description?: string
}

interface Strategy {
  strategy_id: string
  city: string
  state: string
  category: string
  status: string
  total_zones: number
  zones_completed: number
  zones_remaining: number
  businesses_found: number
  estimated_total_businesses?: number
  coverage_area_km2?: number
  strategy_accuracy?: number
  geographic_analysis?: string
  business_distribution_analysis?: string
  zones: Zone[]
  next_zone?: Zone
}

interface ScrapeResult {
  strategy_id: string
  status: string
  zone_scraped: {
    zone_id: string
    priority: string
    lat: number
    lon: number
    radius_km: number
    reason?: string
  }
  results: {
    raw_businesses: number
    qualified_leads: number
    new_businesses: number
  }
  progress: {
    total_zones: number
    zones_completed: number
    zones_remaining: number
    total_businesses_found: number
    estimated_total_businesses?: number
    completion_pct: number
  }
  next_zone_preview?: Zone
}

export function IntelligentCampaignPanel() {
  const [city, setCity] = useState('Los Angeles')
  const [state, setState] = useState('CA')
  const [category, setCategory] = useState('plumbers')
  const [population, setPopulation] = useState<number | ''>(3800000)
  
  const [loading, setLoading] = useState(false)
  const [strategy, setStrategy] = useState<Strategy | null>(null)
  const [scrapeResult, setScrapeResult] = useState<ScrapeResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleCreateStrategy = async () => {
    setLoading(true)
    setError(null)
    setScrapeResult(null)
    
    try {
      const response = await api.post('/intelligent-campaigns/strategies', {
        city,
        state,
        category,
        population: population || undefined,
        force_regenerate: false
      })
      
      setStrategy(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create strategy')
      console.error('Strategy creation error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleScrapeNextZone = async () => {
    if (!strategy) return
    
    setLoading(true)
    setError(null)
    
    try {
      const response = await api.post('/intelligent-campaigns/scrape-zone', {
        strategy_id: strategy.strategy_id,
        limit_per_zone: 50
      })
      
      setScrapeResult(response.data)
      
      // Refresh strategy
      const strategyResponse = await api.get(`/intelligent-campaigns/strategies/${strategy.strategy_id}`)
      setStrategy(strategyResponse.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to scrape zone')
      console.error('Scrape error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleBatchScrape = async () => {
    if (!strategy) return
    
    setLoading(true)
    setError(null)
    
    try {
      await api.post('/intelligent-campaigns/batch-scrape', {
        strategy_id: strategy.strategy_id,
        limit_per_zone: 50,
        max_zones: 5 // Scrape 5 zones at a time
      })
      
      alert('Batch scraping started! This will run in the background.')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start batch scrape')
      console.error('Batch scrape error:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="intelligent-campaign-panel">
      <Card className="panel-card">
        <div className="panel-header">
          <h2>🤖 Intelligent Campaign Orchestration</h2>
          <p className="subtitle">
            Claude analyzes your city and generates the optimal scraping strategy.
            You pick the city, Claude handles the rest.
          </p>
        </div>

        {/* Input Form */}
        <div className="form-section">
          <div className="form-row">
            <div className="form-field">
              <label>City</label>
              <Input
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="Los Angeles"
              />
            </div>
            
            <div className="form-field">
              <label>State</label>
              <Input
                value={state}
                onChange={(e) => setState(e.target.value)}
                placeholder="CA"
                maxLength={2}
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-field">
              <label>Business Category</label>
              <Input
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                placeholder="plumbers"
              />
            </div>
            
            <div className="form-field">
              <label>Population (Optional)</label>
              <Input
                type="number"
                value={population}
                onChange={(e) => setPopulation(e.target.value ? parseInt(e.target.value) : '')}
                placeholder="3800000"
              />
            </div>
          </div>

          <Button
            onClick={handleCreateStrategy}
            disabled={loading || !city || !state || !category}
            className="create-strategy-btn"
          >
            {loading ? <Spinner size="sm" /> : '🧠 Generate Intelligent Strategy'}
          </Button>
        </div>

        {/* Error Display */}
        {error && (
          <div className="error-message">
            ⚠️ {error}
          </div>
        )}

        {/* Strategy Display */}
        {strategy && (
          <div className="strategy-section">
            <div className="strategy-header">
              <h3>📍 Strategy: {strategy.city}, {strategy.state} - {strategy.category}</h3>
              <span className={`status-badge status-${strategy.status}`}>
                {strategy.status}
              </span>
            </div>

            {/* Claude's Analysis */}
            <div className="analysis-section">
              <div className="analysis-card">
                <h4>🗺️ Geographic Analysis</h4>
                <p>{strategy.geographic_analysis}</p>
              </div>
              
              <div className="analysis-card">
                <h4>🏢 Business Distribution</h4>
                <p>{strategy.business_distribution_analysis}</p>
              </div>
            </div>

            {/* Progress Metrics */}
            <div className="metrics-grid">
              <div className="metric-card">
                <div className="metric-value">{strategy.total_zones}</div>
                <div className="metric-label">Total Zones</div>
              </div>
              
              <div className="metric-card">
                <div className="metric-value">{strategy.zones_completed}</div>
                <div className="metric-label">Completed</div>
              </div>
              
              <div className="metric-card">
                <div className="metric-value">{strategy.zones_remaining}</div>
                <div className="metric-label">Remaining</div>
              </div>
              
              <div className="metric-card">
                <div className="metric-value">{strategy.businesses_found}</div>
                <div className="metric-label">Businesses Found</div>
              </div>
              
              {strategy.estimated_total_businesses && (
                <div className="metric-card">
                  <div className="metric-value">{strategy.estimated_total_businesses}</div>
                  <div className="metric-label">Estimated Total</div>
                </div>
              )}
              
              {strategy.coverage_area_km2 && (
                <div className="metric-card">
                  <div className="metric-value">{strategy.coverage_area_km2.toFixed(1)} km²</div>
                  <div className="metric-label">Coverage Area</div>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            {strategy.status === 'active' && strategy.next_zone && (
              <div className="action-section">
                <div className="next-zone-info">
                  <h4>Next Zone: {strategy.next_zone.zone_id}</h4>
                  <p>
                    <strong>Priority:</strong> {strategy.next_zone.priority} | 
                    <strong> Location:</strong> {strategy.next_zone.lat.toFixed(4)}, {strategy.next_zone.lon.toFixed(4)} | 
                    <strong> Radius:</strong> {strategy.next_zone.radius_km}km
                  </p>
                  {strategy.next_zone.reason && (
                    <p className="zone-reason">📌 {strategy.next_zone.reason}</p>
                  )}
                </div>

                <div className="action-buttons">
                  <Button
                    onClick={handleScrapeNextZone}
                    disabled={loading}
                    className="scrape-btn primary"
                  >
                    {loading ? <Spinner size="sm" /> : '🎯 Scrape Next Zone'}
                  </Button>
                  
                  <Button
                    onClick={handleBatchScrape}
                    disabled={loading}
                    className="scrape-btn secondary"
                  >
                    {loading ? <Spinner size="sm" /> : '⚡ Batch Scrape (5 zones)'}
                  </Button>
                </div>
              </div>
            )}

            {strategy.status === 'completed' && (
              <div className="completion-message">
                ✅ Strategy Complete! All {strategy.total_zones} zones have been scraped.
                Found {strategy.businesses_found} businesses.
              </div>
            )}
          </div>
        )}

        {/* Scrape Results */}
        {scrapeResult && (
          <div className="results-section">
            <h3>📊 Zone Results: {scrapeResult.zone_scraped.zone_id}</h3>
            
            <div className="results-grid">
              <div className="result-card">
                <div className="result-value">{scrapeResult.results.raw_businesses}</div>
                <div className="result-label">Raw Businesses</div>
              </div>
              
              <div className="result-card highlight">
                <div className="result-value">{scrapeResult.results.qualified_leads}</div>
                <div className="result-label">Qualified Leads</div>
              </div>
              
              <div className="result-card">
                <div className="result-value">{scrapeResult.results.new_businesses}</div>
                <div className="result-label">New Businesses</div>
              </div>
            </div>

            <div className="progress-bar-container">
              <div className="progress-label">
                Campaign Progress: {scrapeResult.progress.completion_pct}%
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ width: `${scrapeResult.progress.completion_pct}%` }}
                />
              </div>
              <div className="progress-stats">
                {scrapeResult.progress.zones_completed} / {scrapeResult.progress.total_zones} zones
                ({scrapeResult.progress.total_businesses_found} businesses found)
              </div>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}

