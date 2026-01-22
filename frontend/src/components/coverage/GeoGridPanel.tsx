/**
 * Geo-Grid Scraping Panel Component
 * 
 * Provides interface for geo-grid based business discovery, which subdivides
 * large cities into zones for comprehensive coverage.
 */
import { useState } from 'react'
import { Card } from '@/components/ui'
import { api } from '@/services/api'
import type { GeoGridScrapeResponse, StrategyComparison } from '@/types'
import { formatNumber, formatCurrency } from '@/utils/formatting'

interface GeoGridPanelProps {
  /** Callback when scraping completes successfully */
  onScrapeComplete?: () => void
}

export function GeoGridPanel({ onScrapeComplete }: GeoGridPanelProps) {
  // Form state
  const [city, setCity] = useState('')
  const [state, setState] = useState('')
  const [industry, setIndustry] = useState('')
  const [population, setPopulation] = useState(100000)
  const [cityLat, setCityLat] = useState(0)
  const [cityLon, setCityLon] = useState(0)
  
  // UI state
  const [isScrapingActive, setIsScrapingActive] = useState(false)
  const [scrapeResult, setScrapeResult] = useState<GeoGridScrapeResponse | null>(null)
  const [comparison, setComparison] = useState<StrategyComparison | null>(null)
  const [isLoadingComparison, setIsLoadingComparison] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  /**
   * Load and display strategy comparison
   */
  const handleCompareStrategies = async () => {
    if (!city || !state || !population) {
      setErrorMessage('Please fill in city, state, and population')
      return
    }

    setIsLoadingComparison(true)
    setErrorMessage('')
    
    try {
      const data = await api.compareGeoGridStrategy({
        city,
        state,
        population,
      })
      setComparison(data)
    } catch (error: any) {
      setErrorMessage(error.response?.data?.detail || 'Failed to load comparison')
    } finally {
      setIsLoadingComparison(false)
    }
  }

  /**
   * Execute geo-grid scraping
   */
  const handleStartScrape = async () => {
    if (!city || !state || !industry || !cityLat || !cityLon) {
      setErrorMessage('Please fill in all required fields (city, state, industry, coordinates)')
      return
    }

    const confirmMsg = comparison
      ? `This will scrape ${comparison.geo_grid.searches} zones for approximately ${formatCurrency(comparison.geo_grid.cost)}. Continue?`
      : `Start geo-grid scraping for ${city}, ${state}?`

    if (!confirm(confirmMsg)) return

    setIsScrapingActive(true)
    setErrorMessage('')
    setScrapeResult(null)

    try {
      const result = await api.scrapeWithGeoGrid({
        city,
        state,
        industry,
        population,
        city_lat: cityLat,
        city_lon: cityLon,
        limit_per_zone: 50,
        priority: 8,
      })
      
      setScrapeResult(result)
      
      if (result.status === 'completed' || result.status === 'partial') {
        onScrapeComplete?.()
      }
    } catch (error: any) {
      setErrorMessage(error.response?.data?.detail || 'Scraping failed')
    } finally {
      setIsScrapingActive(false)
    }
  }

  /**
   * Reset form to initial state
   */
  const handleReset = () => {
    setCity('')
    setState('')
    setIndustry('')
    setPopulation(100000)
    setCityLat(0)
    setCityLon(0)
    setScrapeResult(null)
    setComparison(null)
    setErrorMessage('')
  }

  return (
    <Card className="geo-grid-panel">
      <div className="card-header">
        <div>
          <h2 className="card-title">🗺️ Geo-Grid Scraping</h2>
          <p className="text-sm text-secondary">
            Subdivide large cities into zones for maximum coverage
          </p>
        </div>
      </div>

      <div className="card-body space-y-6">
        {/* Configuration Form */}
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label" htmlFor="geo-city">
              City <span className="text-error">*</span>
            </label>
            <input
              id="geo-city"
              type="text"
              className="input"
              placeholder="Los Angeles"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              disabled={isScrapingActive}
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="geo-state">
              State <span className="text-error">*</span>
            </label>
            <input
              id="geo-state"
              type="text"
              className="input"
              placeholder="CA"
              maxLength={2}
              value={state}
              onChange={(e) => setState(e.target.value.toUpperCase())}
              disabled={isScrapingActive}
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="geo-industry">
              Industry <span className="text-error">*</span>
            </label>
            <input
              id="geo-industry"
              type="text"
              className="input"
              placeholder="plumbers"
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              disabled={isScrapingActive}
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="geo-population">
              Population
            </label>
            <input
              id="geo-population"
              type="number"
              className="input"
              value={population}
              onChange={(e) => setPopulation(parseInt(e.target.value) || 0)}
              disabled={isScrapingActive}
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="geo-lat">
              Latitude <span className="text-error">*</span>
            </label>
            <input
              id="geo-lat"
              type="number"
              step="0.000001"
              className="input"
              placeholder="34.052235"
              value={cityLat || ''}
              onChange={(e) => setCityLat(parseFloat(e.target.value) || 0)}
              disabled={isScrapingActive}
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="geo-lon">
              Longitude <span className="text-error">*</span>
            </label>
            <input
              id="geo-lon"
              type="number"
              step="0.000001"
              className="input"
              placeholder="-118.243683"
              value={cityLon || ''}
              onChange={(e) => setCityLon(parseFloat(e.target.value) || 0)}
              disabled={isScrapingActive}
            />
          </div>
        </div>

        {/* Error Display */}
        {errorMessage && (
          <div className="alert alert-error">
            {errorMessage}
          </div>
        )}

        {/* Action Buttons */}
        <div className="btn-group">
          <button
            onClick={handleCompareStrategies}
            disabled={isScrapingActive || isLoadingComparison}
            className="btn btn-secondary"
          >
            {isLoadingComparison ? (
              <>
                <span className="spinner-sm" />
                Analyzing...
              </>
            ) : (
              '📊 Compare Strategies'
            )}
          </button>

          <button
            onClick={handleStartScrape}
            disabled={isScrapingActive}
            className="btn btn-primary"
          >
            {isScrapingActive ? (
              <>
                <span className="spinner-sm" />
                Scraping zones...
              </>
            ) : (
              '🚀 Start Geo-Grid Scrape'
            )}
          </button>

          {(scrapeResult || comparison) && (
            <button
              onClick={handleReset}
              className="btn btn-outline"
            >
              Reset
            </button>
          )}
        </div>

        {/* Strategy Comparison */}
        {comparison && (
          <StrategyComparisonDisplay comparison={comparison} />
        )}

        {/* Scrape Results */}
        {scrapeResult && (
          <ScrapeResultDisplay result={scrapeResult} />
        )}
      </div>
    </Card>
  )
}

/**
 * Display strategy comparison data
 */
interface StrategyComparisonDisplayProps {
  comparison: StrategyComparison
}

function StrategyComparisonDisplay({ comparison }: StrategyComparisonDisplayProps) {
  const { traditional, geo_grid, recommendation } = comparison

  return (
    <div className="strategy-comparison">
      <h3 className="font-semibold mb-4">Strategy Comparison</h3>
      
      <div className="comparison-grid">
        {/* Traditional Approach */}
        <div className={`comparison-card ${recommendation === 'traditional' ? 'recommended' : ''}`}>
          <div className="comparison-header">
            <h4 className="font-semibold">Traditional Approach</h4>
            {recommendation === 'traditional' && (
              <span className="badge badge-success">Recommended</span>
            )}
          </div>
          <div className="comparison-stats">
            <div className="stat-row">
              <span className="stat-label">Searches:</span>
              <span className="stat-value">{traditional.searches}</span>
            </div>
            <div className="stat-row">
              <span className="stat-label">Expected Results:</span>
              <span className="stat-value">{formatNumber(traditional.expected_results)}</span>
            </div>
            <div className="stat-row">
              <span className="stat-label">Coverage:</span>
              <span className="stat-value">{traditional.coverage_km2.toFixed(0)} km²</span>
            </div>
            <div className="stat-row">
              <span className="stat-label">Est. Cost:</span>
              <span className="stat-value text-primary">{formatCurrency(traditional.cost)}</span>
            </div>
          </div>
        </div>

        {/* Geo-Grid Approach */}
        <div className={`comparison-card ${recommendation === 'geo_grid' ? 'recommended' : ''}`}>
          <div className="comparison-header">
            <h4 className="font-semibold">Geo-Grid Approach</h4>
            {recommendation === 'geo_grid' && (
              <span className="badge badge-success">Recommended</span>
            )}
          </div>
          <div className="comparison-stats">
            <div className="stat-row">
              <span className="stat-label">Grid Size:</span>
              <span className="stat-value">{geo_grid.grid_size}</span>
            </div>
            <div className="stat-row">
              <span className="stat-label">Searches:</span>
              <span className="stat-value">{geo_grid.searches}</span>
            </div>
            <div className="stat-row">
              <span className="stat-label">Expected Results:</span>
              <span className="stat-value">{formatNumber(geo_grid.expected_results)}</span>
            </div>
            <div className="stat-row">
              <span className="stat-label">Coverage:</span>
              <span className="stat-value">{geo_grid.coverage_km2.toFixed(0)} km²</span>
            </div>
            <div className="stat-row">
              <span className="stat-label">Est. Cost:</span>
              <span className="stat-value text-primary">{formatCurrency(geo_grid.cost)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * Display scrape results
 */
interface ScrapeResultDisplayProps {
  result: GeoGridScrapeResponse
}

function ScrapeResultDisplay({ result }: ScrapeResultDisplayProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-success'
      case 'partial': return 'text-warning'
      case 'failed': return 'text-error'
      default: return 'text-secondary'
    }
  }

  return (
    <div className="scrape-results">
      <div className="results-header">
        <h3 className="font-semibold">Scrape Results</h3>
        <span className={`badge ${getStatusColor(result.status)}`}>
          {result.status.toUpperCase()}
        </span>
      </div>

      {/* Summary Stats */}
      <div className="stats-grid grid-cols-4">
        <div className="stat-card">
          <div className="stat-label">Zones Scraped</div>
          <div className="stat-value">{result.zones_scraped}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Found</div>
          <div className="stat-value text-info">{formatNumber(result.total_scraped)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Qualified</div>
          <div className="stat-value text-success">{formatNumber(result.total_qualified)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Saved</div>
          <div className="stat-value text-primary">{formatNumber(result.total_saved)}</div>
        </div>
      </div>

      {/* Zone Details */}
      {result.zone_results && result.zone_results.length > 0 && (
        <div className="zone-results">
          <h4 className="text-sm font-semibold mb-2">Zone Details</h4>
          <div className="zone-results-grid">
            {result.zone_results.map((zone, index) => (
              <div
                key={index}
                className={`zone-result-card ${zone.error ? 'error' : 'success'}`}
              >
                <div className="zone-id">{zone.zone_id}</div>
                {zone.error ? (
                  <div className="text-error text-xs">{zone.error}</div>
                ) : (
                  <div className="zone-stats">
                    <span className="text-xs">
                      {zone.scraped} found • {zone.qualified} qualified • {zone.saved} saved
                    </span>
                    {zone.has_more && (
                      <span className="badge badge-sm badge-info">More available</span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Message */}
      {result.message && (
        <div className="alert alert-info">
          {result.message}
        </div>
      )}

      {/* Error */}
      {result.error && (
        <div className="alert alert-error">
          {result.error}
        </div>
      )}
    </div>
  )
}

