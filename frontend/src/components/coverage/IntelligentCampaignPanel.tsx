import { useState, useEffect, useRef, useCallback } from 'react'
import { Card } from '@/components/ui'
import { api } from '@/services/api'
import { US_STATES } from '@/data/states'
import { getCitiesForState } from '@/data/cities'
import { CoverageBreakdownPanel } from './CoverageBreakdownPanel'
import { ZoneStatisticsCard } from './ZoneStatisticsCard'
import { ScrapeProgress } from '@/components/scraping'
import './IntelligentCampaignPanel.css'

interface Zone {
  zone_id: string
  city?: string
  target_city?: string
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
  scraped_zone_ids?: string[]
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
    // Phase 3: New website metrics
    with_websites?: number
    without_websites?: number
    invalid_websites?: number
    queued_for_generation?: number
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

interface IntelligentCampaignPanelProps {
  onCampaignUpdate?: () => void
}

export function IntelligentCampaignPanel({ onCampaignUpdate }: IntelligentCampaignPanelProps) {
  // Form state
  const [state, setState] = useState('CA')
  const [city, setCity] = useState('Los Angeles')
  const [category, setCategory] = useState('plumbers')
  const [draftMode, setDraftMode] = useState(true) // Default to draft mode for safety
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null) // For manual zone selection
  const [forceRescrape, setForceRescrape] = useState(false) // Allow re-scraping zones
  
  // Data state
  const [availableCities, setAvailableCities] = useState<string[]>([])
  const [businessCategories, setBusinessCategories] = useState<string[]>([])
  
  // Campaign state
  const [loading, setLoading] = useState(false)
  const [strategy, setStrategy] = useState<Strategy | null>(null)
  const [scrapeResult, setScrapeResult] = useState<ScrapeResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  
  // Phase 2: Async scraping with SSE progress
  const [scrapeSessionId, setScrapeSessionId] = useState<string | null>(null)
  const [isScrapingAsync, setIsScrapingAsync] = useState(false)

  // Batch scrape progress tracking
  const [isBatchRunning, setIsBatchRunning] = useState(false)
  const [batchStartZones, setBatchStartZones] = useState(0)
  const [batchTargetZones, setBatchTargetZones] = useState(5)
  const [batchConfirmMode, setBatchConfirmMode] = useState(false)
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const noChangeCountRef = useRef(0)

  // Load business categories on mount
  useEffect(() => {
    loadBusinessCategories()
  }, [])

  // Update available cities when state changes
  useEffect(() => {
    const cities = getCitiesForState(state)
    setAvailableCities(cities)
    // Set first city as default if current city not in list
    if (cities.length > 0 && !cities.includes(city)) {
      setCity(cities[0])
    }
  }, [state])

  const loadBusinessCategories = async () => {
    try {
      const categories = await api.getBusinessCategorySearchTerms()
      setBusinessCategories(categories)
    } catch (err) {
      console.error('Failed to load business categories:', err)
      // Fallback to some default categories
      setBusinessCategories(['plumbers', 'electricians', 'hvac', 'roofers', 'lawyers', 'dentists'])
    }
  }

  const handleCreateStrategy = async () => {
    console.log('🔵 handleCreateStrategy called', { city, state, category, loading })
    setLoading(true)
    setError(null)
    setScrapeResult(null)
    
    try {
      console.log('🔵 Calling api.createIntelligentStrategy...')
      const response = await api.createIntelligentStrategy({
        city,
        state,
        category,
        force_regenerate: false
      })
      
      console.log('✅ Strategy response:', response)
      setStrategy(response)
    } catch (err: any) {
      console.error('❌ Strategy creation error:', err)
      setError(err.response?.data?.detail || 'Failed to create strategy')
    } finally {
      setLoading(false)
    }
  }

  const handleScrapeNextZone = async () => {
    if (!strategy) return
    
    setLoading(true)
    setError(null)
    setScrapeResult(null) // Clear previous results
    
    try {
      console.log('🔵 Starting async zone scrape...', { 
        zone_id: selectedZoneId || 'auto (next)',
        force_rescrape: forceRescrape 
      })
      
      // Phase 2: Use new async API with SSE progress
      const response = await api.startScrape({
        zone_id: selectedZoneId || strategy.next_zone?.zone_id || '',
        city: city,
        state: state,
        category: category,
        country: 'US',
        limit_per_zone: 50,
        strategy_id: strategy.strategy_id
      })
      
      console.log('✅ Scrape queued:', response)
      
      // Set session ID to start SSE stream
      setScrapeSessionId(response.session_id)
      setIsScrapingAsync(true)
      setLoading(false) // No longer blocking!
      
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to start scrape'
      setError(errorMessage)
      setLoading(false)
      
      console.error('❌ Failed to queue scrape:', err)
    }
  }
  
  const handleScrapeComplete = async (summary: Record<string, number>) => {
    console.log('🎉 Scrape completed!', summary)
    
    setIsScrapingAsync(false)
    setScrapeSessionId(null)
    
    // Refresh strategy to get updated counts
    if (strategy) {
      try {
        const strategyResponse = await api.getIntelligentStrategy(strategy.strategy_id)
        setStrategy(strategyResponse)
        
        // Notify parent
        if (onCampaignUpdate) {
          onCampaignUpdate()
        }
      } catch (err) {
        console.error('Failed to refresh strategy:', err)
      }
    }
  }
  
  const handleScrapeError = (errorMessage: string) => {
    console.error('❌ Scrape error:', errorMessage)
    setError(errorMessage)
    setIsScrapingAsync(false)
    setScrapeSessionId(null)
  }

  const stopBatchPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }, [])

  const startBatchPolling = useCallback((strategyId: string, startingZones: number) => {
    noChangeCountRef.current = 0
    let lastZonesCompleted = startingZones

    pollIntervalRef.current = setInterval(async () => {
      try {
        // Use the quiet variant — a 401 (e.g. token expiry) stops polling
        // gracefully instead of triggering a full logout
        const updated = await api.getIntelligentStrategyQuiet(strategyId)
        setStrategy(updated)

        if (updated.zones_completed === updated.total_zones) {
          stopBatchPolling()
          setIsBatchRunning(false)
          if (onCampaignUpdate) onCampaignUpdate()
          return
        }

        if (updated.zones_completed === lastZonesCompleted) {
          noChangeCountRef.current += 1
          // After ~3 minutes of no change (18 polls × 10s), assume done or stalled
          if (noChangeCountRef.current >= 18) {
            stopBatchPolling()
            setIsBatchRunning(false)
            if (onCampaignUpdate) onCampaignUpdate()
          }
        } else {
          noChangeCountRef.current = 0
          lastZonesCompleted = updated.zones_completed
        }
      } catch (err: any) {
        if (err?.response?.status === 401) {
          // Token expired mid-poll — stop polling silently, don't logout
          console.warn('Polling stopped: session expired. Please refresh the page.')
          stopBatchPolling()
          setIsBatchRunning(false)
        } else {
          console.error('Polling error:', err)
        }
      }
    }, 10_000) // poll every 10 seconds
  }, [stopBatchPolling, onCampaignUpdate])

  // Clean up interval on unmount
  useEffect(() => {
    return () => stopBatchPolling()
  }, [stopBatchPolling])

  const handleBatchScrapeConfirm = async () => {
    if (!strategy) return
    setBatchConfirmMode(false)
    setLoading(true)
    setError(null)

    try {
      await api.batchScrapeIntelligentStrategy({
        strategy_id: strategy.strategy_id,
        limit_per_zone: 200,
        max_zones: batchTargetZones,
        draft_mode: draftMode
      })

      setBatchStartZones(strategy.zones_completed)
      setIsBatchRunning(true)
      startBatchPolling(strategy.strategy_id, strategy.zones_completed)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start batch scrape')
    } finally {
      setLoading(false)
    }
  }

  const handleBatchScrape = () => {
    if (!strategy) return
    setBatchTargetZones(5)
    setBatchConfirmMode(true)
  }

  return (
    <div className="intelligent-campaign-panel">
      <Card className="panel-card">
        <div className="panel-header">
          <h2>🤖 Intelligent Campaign Orchestration</h2>
          <p className="subtitle">
            Claude analyzes your city and generates the optimal scraping strategy.
            You pick the city + category, Claude handles the rest.
          </p>
        </div>

        {/* Input Form */}
        <div className="form-section">
          <div className="form-row">
            <div className="form-field">
              <label>State *</label>
              <select
                className="form-input"
                value={state}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setState(e.target.value)}
              >
                {US_STATES.map((s) => (
                  <option key={s.code} value={s.code}>
                    {s.name} ({s.code})
                  </option>
                ))}
              </select>
            </div>
            
            <div className="form-field">
              <label>City *</label>
              <select
                className="form-input"
                value={city}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setCity(e.target.value)}
              >
                {availableCities.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-field">
              <label>Business Category *</label>
              <select
                className="form-input"
                value={category}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setCategory(e.target.value)}
              >
                {businessCategories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat.charAt(0).toUpperCase() + cat.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          </div>
          
          <div className="info-box">
            <span className="info-icon">ℹ️</span>
            <p>
              Claude will automatically fetch city population and geographic data to optimize zone placement.
              Just select your target city and business category!
            </p>
          </div>

          {/* Draft Mode Toggle */}
          <div className="draft-mode-section">
            <label className="draft-mode-toggle">
              <input
                type="checkbox"
                checked={draftMode}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDraftMode(e.target.checked)}
                className="draft-mode-checkbox"
              />
              <div className="draft-mode-content">
                <div className="draft-mode-header">
                  <span className="draft-mode-icon">{draftMode ? '📋' : '🚀'}</span>
                  <span className="draft-mode-title">
                    {draftMode ? 'Draft Mode' : 'Live Mode (Auto-Send)'}
                  </span>
                </div>
                <p className="draft-mode-description">
                  {draftMode ? (
                    <>Find businesses and save for <strong>manual review</strong> (recommended for first run)</>
                  ) : (
                    <>Find businesses and <strong>automatically send</strong> outreach messages</>
                  )}
                </p>
              </div>
            </label>
          </div>

          <button
            onClick={handleCreateStrategy}
            disabled={loading || !city || !state || !category}
            className="create-strategy-btn"
          >
            {loading ? '⏳ Generating Strategy...' : '🧠 Generate Intelligent Strategy'}
          </button>
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

            {/* Action Buttons - Show zone selector for ALL strategies (for rescraping) */}
            {strategy && strategy.zones && strategy.zones.length > 0 && (
              <div className="action-section">
                {/* Zone Selector */}
                <div className="zone-selector-section">
                  <div className="form-field">
                    <label>Select Zone to Scrape</label>
                    <select
                      className="form-input"
                      value={selectedZoneId || ''}
                      onChange={(e) => setSelectedZoneId(e.target.value || null)}
                    >
                      <option value="">Auto (Next Unscraped Zone)</option>
                      {strategy.zones.map((zone) => {
                        const isScraped = strategy.scraped_zone_ids?.includes(zone.zone_id) || false
                        const prefix = isScraped ? '✓ SCRAPED: ' : ''
                        const label = `${prefix}${zone.zone_id} - ${zone.city || zone.target_city || zone.area_description} (${zone.priority})`
                        return (
                          <option key={zone.zone_id} value={zone.zone_id}>
                            {label}
                          </option>
                        )
                      })}
                    </select>
                  </div>
                  
                  <label className="checkbox-label" style={{ marginTop: '10px' }}>
                    <input
                      type="checkbox"
                      checked={forceRescrape}
                      onChange={(e) => setForceRescrape(e.target.checked)}
                    />
                    <span>Force Rescrape (allow re-scraping already-scraped zones)</span>
                  </label>
                </div>

                {strategy.next_zone && (
                  <div className="next-zone-info">
                    <h4>
                      {selectedZoneId 
                        ? `Selected Zone: ${selectedZoneId}` 
                        : `Next Zone: ${strategy.next_zone.zone_id}`}
                    </h4>
                    <p>
                      <strong>Priority:</strong> {strategy.next_zone.priority} | 
                      <strong> Location:</strong> {strategy.next_zone.lat.toFixed(4)}, {strategy.next_zone.lon.toFixed(4)} | 
                      <strong> Radius:</strong> {strategy.next_zone.radius_km}km
                    </p>
                    {strategy.next_zone.reason && (
                      <p className="zone-reason">📌 {strategy.next_zone.reason}</p>
                    )}
                  </div>
                )}

                {!strategy.next_zone && !selectedZoneId && !forceRescrape && (
                  <div className="info-box" style={{ marginTop: '15px' }}>
                    <span className="info-icon">ℹ️</span>
                    <p>
                      All zones have been scraped. To rescrape a zone, select it from the dropdown and check "Force Rescrape".
                    </p>
                  </div>
                )}

                {/* Batch Confirm Prompt */}
                {batchConfirmMode && (
                  <div className="batch-confirm-box">
                    <div className="batch-confirm-header">
                      <span className="batch-confirm-icon">⚡</span>
                      <span className="batch-confirm-title">Start Batch Scrape?</span>
                    </div>
                    <p className="batch-confirm-description">
                      This will scrape <strong>{batchTargetZones} zones</strong> in{' '}
                      <strong>{draftMode ? 'Draft Mode' : 'Live Mode'}</strong>.{' '}
                      {draftMode
                        ? 'Businesses will be saved for review — no outreach will be sent.'
                        : 'Outreach will be sent automatically to qualified leads.'}
                    </p>
                    <div className="batch-confirm-actions">
                      <button
                        onClick={handleBatchScrapeConfirm}
                        className="scrape-btn primary"
                      >
                        Confirm &amp; Start
                      </button>
                      <button
                        onClick={() => setBatchConfirmMode(false)}
                        className="scrape-btn cancel"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}

                {/* Batch In-Progress Banner */}
                {isBatchRunning && strategy && (
                  <div className="batch-progress-banner">
                    <div className="batch-progress-header">
                      <span className="batch-spinner" />
                      <span className="batch-progress-title">
                        Batch scraping in progress&hellip;
                      </span>
                      <span className="batch-progress-count">
                        {strategy.zones_completed - batchStartZones} / {batchTargetZones} zones done
                      </span>
                    </div>
                    <div className="batch-progress-track">
                      <div
                        className="batch-progress-fill"
                        style={{
                          width: `${Math.min(
                            100,
                            ((strategy.zones_completed - batchStartZones) / batchTargetZones) * 100
                          )}%`
                        }}
                      />
                    </div>
                    <p className="batch-progress-hint">
                      The page auto-updates every 10 seconds. You can keep working while zones complete.
                    </p>
                  </div>
                )}

                <div className="action-buttons">
                  <button
                    onClick={handleScrapeNextZone}
                    disabled={loading || isScrapingAsync || isBatchRunning || (!selectedZoneId && !strategy.next_zone && !forceRescrape)}
                    className="scrape-btn primary"
                  >
                    {isScrapingAsync || loading
                      ? 'Starting…'
                      : forceRescrape
                        ? 'Rescrape This Zone'
                        : selectedZoneId
                          ? 'Scrape Selected Zone'
                          : 'Scrape Next Zone'}
                  </button>
                  
                  {strategy.next_zone && (
                    <button
                      onClick={handleBatchScrape}
                      disabled={loading || isScrapingAsync || isBatchRunning || batchConfirmMode}
                      className="scrape-btn secondary"
                    >
                      {isBatchRunning ? 'Batch Running…' : 'Batch Scrape (5 zones)'}
                    </button>
                  )}
                </div>
                
                {/* Phase 2: Real-time progress with SSE */}
                {scrapeSessionId && isScrapingAsync && (
                  <ScrapeProgress 
                    sessionId={scrapeSessionId}
                    onComplete={handleScrapeComplete}
                    onError={handleScrapeError}
                    showEventLog={false}
                  />
                )}
              </div>
            )}

            {strategy.status === 'completed' && !selectedZoneId && !forceRescrape && (
              <div className="completion-message">
                ✅ Strategy Complete! All {strategy.total_zones} zones have been scraped. 
                <span style={{ marginLeft: '10px', fontSize: '0.9em' }}>
                  (You can still rescrape zones using the selector above)
                </span>
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

            {/* Phase 3: New Website Metrics */}
            {(scrapeResult.results.with_websites !== undefined || 
              scrapeResult.results.without_websites !== undefined) && (
              <div className="website-metrics-grid">
                {scrapeResult.results.with_websites !== undefined && (
                  <div className="result-card website-valid">
                    <div className="result-value">{scrapeResult.results.with_websites}</div>
                    <div className="result-label">With Valid Websites</div>
                  </div>
                )}
                
                {scrapeResult.results.without_websites !== undefined && (
                  <div className="result-card website-none">
                    <div className="result-value">{scrapeResult.results.without_websites}</div>
                    <div className="result-label">Without Websites</div>
                  </div>
                )}
                
                {scrapeResult.results.invalid_websites !== undefined && scrapeResult.results.invalid_websites > 0 && (
                  <div className="result-card website-invalid">
                    <div className="result-value">{scrapeResult.results.invalid_websites}</div>
                    <div className="result-label">Invalid Websites</div>
                  </div>
                )}
                
                {scrapeResult.results.queued_for_generation !== undefined && scrapeResult.results.queued_for_generation > 0 && (
                  <div className="result-card website-generating">
                    <div className="result-value">{scrapeResult.results.queued_for_generation}</div>
                    <div className="result-label">Queued for Generation</div>
                  </div>
                )}
              </div>
            )}

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

            {/* Phase 3: Zone Statistics Card (Persistent Details) */}
            <div className="zone-stats-container">
              <h4>Detailed Zone Statistics</h4>
              <ZoneStatisticsCard 
                zoneId={scrapeResult.zone_scraped.zone_id}
                autoLoad={true}
              />
            </div>
          </div>
        )}

        {/* Phase 3: Comprehensive Strategy Breakdown (Always visible when strategy exists) */}
        {strategy && strategy.zones_completed > 0 && (
          <div className="strategy-breakdown-container">
            <CoverageBreakdownPanel 
              strategyId={strategy.strategy_id}
              autoLoad={true}
              showZoneDetails={true}
            />
          </div>
        )}
      </Card>
    </div>
  )
}
