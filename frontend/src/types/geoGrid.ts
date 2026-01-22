/**
 * Geographic Grid System Types
 * 
 * Types for the geo-grid business discovery system that subdivides
 * cities into geographic zones for comprehensive coverage.
 */

/** Grid configuration for a city based on population */
export interface GeoGridConfig {
  /** Number of rows in the grid */
  rows: number
  /** Number of columns in the grid */
  cols: number
  /** Total number of zones (rows × cols) */
  total_zones: number
  /** Search radius per zone in kilometers */
  zone_radius_km: number
  /** Approximate coverage area in km² */
  approx_coverage_km2: number
}

/** Individual geographic zone within a city */
export interface GeoZone {
  /** Zone identifier (e.g., "2x3" for row 2, col 3) */
  zone_id: string
  /** Center latitude of zone */
  center_lat: number
  /** Center longitude of zone */
  center_lon: number
  /** City name */
  city: string
  /** State code */
  state: string
  /** Search radius for this zone */
  radius_km: number
}

/** City data for geo-grid scraping */
export interface GeoGridCity {
  /** City name */
  city: string
  /** State code (e.g., "CA", "TX") */
  state: string
  /** City center latitude */
  lat: number
  /** City center longitude */
  lon: number
  /** City population */
  population: number
}

/** Request to scrape a location with geo-grid subdivision */
export interface GeoGridScrapeRequest {
  /** City name */
  city: string
  /** State code */
  state: string
  /** Business industry/category */
  industry: string
  /** City population (for grid calculation) */
  population: number
  /** City center latitude */
  city_lat: number
  /** City center longitude */
  city_lon: number
  /** Maximum results per zone (default: 50) */
  limit_per_zone?: number
  /** Priority level (1-10) */
  priority?: number
}

/** Result from a single zone scrape */
export interface ZoneResult {
  /** Zone identifier */
  zone_id: string
  /** Coverage grid ID created/used */
  coverage_id?: string
  /** Number of businesses scraped */
  scraped: number
  /** Number of qualified businesses */
  qualified: number
  /** Number of new businesses saved */
  saved: number
  /** Whether more results are available */
  has_more?: boolean
  /** Error message if failed */
  error?: string
}

/** Complete geo-grid scrape response */
export interface GeoGridScrapeResponse {
  /** Overall status */
  status: 'completed' | 'failed' | 'partial'
  /** Location scraped */
  location: string
  /** Industry scraped */
  industry: string
  /** Number of zones scraped */
  zones_scraped: number
  /** Total businesses found across all zones */
  total_scraped: number
  /** Total qualified businesses */
  total_qualified: number
  /** Total new businesses saved */
  total_saved: number
  /** Individual zone results */
  zone_results: ZoneResult[]
  /** Success message */
  message?: string
  /** Error message if failed */
  error?: string
}

/** Strategy comparison data */
export interface StrategyComparison {
  /** City being analyzed */
  city: string
  /** State code */
  state: string
  /** City population */
  population: number
  /** Traditional approach metrics */
  traditional: {
    searches: number
    expected_results: number
    coverage_km2: number
    cost: number
  }
  /** Geo-grid approach metrics */
  geo_grid: {
    grid_size: string
    total_zones: number
    searches: number
    expected_results: number
    coverage_km2: number
    cost: number
  }
  /** Recommended strategy */
  recommendation: 'traditional' | 'geo_grid'
}

/** Website validation status */
export type WebsiteStatus = 'valid' | 'invalid' | 'none'

/** Enhanced coverage grid with geo-zone information */
export interface GeoGridCoverage {
  id: string
  country: string
  state: string
  city: string
  industry: string
  
  /** Zone information (if subdivided) */
  zone_id?: string
  zone_lat?: string
  zone_lon?: string
  zone_radius_km?: string
  
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  priority: number
  
  /** Metrics */
  lead_count: number
  qualified_count: number
  qualification_rate?: number
  
  /** Timing */
  last_scraped_at?: string
  cooldown_until?: string
  next_scheduled?: string
  
  created_at: string
  updated_at: string
}

