# Intelligent Campaign Management System - Analysis & Design

## Overview
Transform the geo-grid scraping system into an AI-driven campaign manager where users simply select a city, and the system intelligently handles all other decisions.

## Current vs Proposed Flow

### Current (Manual)
```
User → Enter city, state, industry, lat, lon, population → Execute scrape
```
**Problems:**
- User must know lat/lon coordinates
- User manually selects each industry
- No tracking of what's already been scraped
- Risk of duplicate scraping
- No systematic coverage guarantee

### Proposed (Intelligent)
```
User → Select city → System analyzes coverage → Shows recommendation → Approve → Auto-execute
```
**Benefits:**
- Minimal user input
- Intelligent industry selection
- Automatic coverage tracking
- No duplicate scraping
- Guaranteed comprehensive coverage

---

## Architecture Design

### Option 1: Rule-Based Intelligence (Recommended for MVP)
**No LLM required** - Uses smart algorithms and database queries

#### Components:

1. **Geocoding Service**
   ```python
   def geocode_city(city_name: str, state: str) -> CityData:
       # Use OpenStreetMap Nominatim (free) or Google Geocoding API
       # Returns: lat, lon, population, boundaries
   ```

2. **Coverage Analyzer**
   ```python
   def analyze_city_coverage(city: str, state: str) -> CoverageReport:
       # Query coverage_grid table
       # Find which industries already scraped
       # Calculate completion percentage
       # Identify gaps in coverage
   ```

3. **Industry Recommender**
   ```python
   def recommend_next_industries(city: str, count: int = 10) -> List[Industry]:
       # Load all 200+ categories
       # Filter out already-scraped industries
       # Prioritize by:
       #   - High-value categories (real estate, legal, medical)
       #   - Categories with higher business density
       #   - User's custom priorities
   ```

4. **Campaign Planner**
   ```python
   def create_campaign_plan(city: str, budget: float) -> CampaignPlan:
       # Calculate grid zones for city
       # Recommend industries to cover
       # Estimate costs (zones × industries × $0.50)
       # Create execution schedule
   ```

5. **Auto-Executor**
   ```python
   def execute_campaign(campaign_id: str):
       # Execute each industry × zone combination
       # Track progress in database
       # Handle failures gracefully
       # Report completion
   ```

---

### Option 2: LLM-Enhanced Intelligence (Future Enhancement)
Add AI capabilities for advanced decision-making

#### LLM Use Cases:

1. **Industry Relevance Analysis**
   ```
   Prompt: "For [City], which business industries would have the highest 
   demand for website services? Consider local economy, population demographics, 
   and market trends."
   ```

2. **Coverage Strategy Optimization**
   ```
   Prompt: "Given these scraping results for [City], which industries should 
   we prioritize next to maximize lead quality and ROI?"
   ```

3. **Campaign Insights**
   ```
   Prompt: "Analyze this campaign data and provide insights on market saturation, 
   high-performing industries, and recommendations for future campaigns."
   ```

---

## Database Schema Extensions

### Campaign Tracking Tables

```sql
-- Master campaign record
CREATE TABLE intelligent_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- City information
    city VARCHAR(100) NOT NULL,
    state VARCHAR(2) NOT NULL,
    city_lat NUMERIC(10, 8),
    city_lon NUMERIC(11, 8),
    population INT,
    
    -- Campaign configuration
    strategy VARCHAR(50) DEFAULT 'comprehensive', -- 'comprehensive', 'targeted', 'quick'
    max_budget NUMERIC(10, 2),
    industries_per_batch INT DEFAULT 10,
    
    -- Status tracking
    status VARCHAR(20) DEFAULT 'planning', -- 'planning', 'approved', 'running', 'paused', 'completed', 'failed'
    
    -- Progress metrics
    total_zones INT,
    total_industries INT,
    completed_tasks INT DEFAULT 0,
    failed_tasks INT DEFAULT 0,
    
    -- Results
    total_businesses_found INT DEFAULT 0,
    total_qualified_leads INT DEFAULT 0,
    estimated_cost NUMERIC(10, 2),
    actual_cost NUMERIC(10, 2) DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- User
    created_by VARCHAR(255),
    
    INDEX idx_city_state (city, state),
    INDEX idx_status (status)
);

-- Individual scraping tasks within campaign
CREATE TABLE campaign_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES intelligent_campaigns(id) ON DELETE CASCADE,
    
    -- Task details
    industry VARCHAR(100) NOT NULL,
    zone_id VARCHAR(50),
    zone_lat NUMERIC(10, 8),
    zone_lon NUMERIC(11, 8),
    zone_radius_km NUMERIC(5, 2),
    
    -- Execution
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed', 'skipped'
    priority INT DEFAULT 5,
    
    -- Results
    businesses_found INT DEFAULT 0,
    businesses_qualified INT DEFAULT 0,
    businesses_saved INT DEFAULT 0,
    cost NUMERIC(10, 2) DEFAULT 0,
    
    -- Error handling
    retry_count INT DEFAULT 0,
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    executed_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Link to coverage_grid
    coverage_grid_id UUID,
    
    INDEX idx_campaign_status (campaign_id, status),
    INDEX idx_priority (campaign_id, priority DESC)
);

-- Campaign execution logs
CREATE TABLE campaign_execution_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES intelligent_campaigns(id) ON DELETE CASCADE,
    
    event_type VARCHAR(50), -- 'started', 'task_completed', 'task_failed', 'paused', 'resumed', 'completed'
    message TEXT,
    metadata JSONB,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_campaign_time (campaign_id, created_at DESC)
);
```

---

## API Endpoints

### 1. Analyze City
```
POST /api/v1/campaigns/intelligent/analyze
{
  "city": "Los Angeles",
  "state": "CA"
}

Response:
{
  "city_data": {
    "name": "Los Angeles",
    "state": "CA",
    "lat": 34.0522,
    "lon": -118.2437,
    "population": 3900000
  },
  "coverage_analysis": {
    "total_industries": 250,
    "scraped_industries": 45,
    "completion_percentage": 18,
    "missing_industries": 205,
    "last_scraped": "2026-01-20T10:30:00Z"
  },
  "grid_info": {
    "recommended_grid_size": "5x5",
    "total_zones": 25,
    "zone_radius_km": 8,
    "coverage_area_km2": 5026
  },
  "recommendations": {
    "next_industries": [
      {"name": "Real Estate Agents", "priority": 10, "estimated_leads": 500},
      {"name": "Law Firms", "priority": 9, "estimated_leads": 300},
      ...
    ],
    "estimated_cost": 625.00,
    "estimated_duration": "~2 hours"
  }
}
```

### 2. Create Campaign
```
POST /api/v1/campaigns/intelligent/create
{
  "city": "Los Angeles",
  "state": "CA",
  "strategy": "comprehensive",  // or "targeted", "quick"
  "max_budget": 500,            // optional
  "industries_count": 20,       // how many industries to scrape
  "auto_start": false           // if true, starts immediately
}

Response:
{
  "campaign_id": "uuid",
  "status": "planning",
  "plan": {
    "total_zones": 25,
    "industries": [...],
    "total_tasks": 500,
    "estimated_cost": 250.00,
    "estimated_duration": "~4 hours"
  }
}
```

### 3. Execute Campaign
```
POST /api/v1/campaigns/intelligent/{campaign_id}/start

Response:
{
  "campaign_id": "uuid",
  "status": "running",
  "started_at": "2026-01-22T...",
  "progress": {
    "total_tasks": 500,
    "completed": 0,
    "failed": 0,
    "pending": 500
  }
}
```

### 4. Monitor Campaign
```
GET /api/v1/campaigns/intelligent/{campaign_id}/status

Response:
{
  "campaign_id": "uuid",
  "status": "running",
  "progress": {
    "percentage": 45,
    "completed_tasks": 225,
    "failed_tasks": 5,
    "pending_tasks": 270
  },
  "current_task": {
    "industry": "Plumbers",
    "zone": "3x2",
    "status": "running"
  },
  "results": {
    "businesses_found": 11250,
    "qualified_leads": 4500,
    "actual_cost": 112.50
  },
  "estimated_completion": "2026-01-22T14:30:00Z"
}
```

### 5. Get Campaign History
```
GET /api/v1/campaigns/intelligent?city=Los Angeles&state=CA

Response:
{
  "campaigns": [
    {
      "id": "uuid",
      "city": "Los Angeles",
      "status": "completed",
      "industries_covered": 50,
      "leads_generated": 12500,
      "cost": 625.00,
      "completed_at": "2026-01-20T..."
    },
    ...
  ]
}
```

---

## UI Components

### 1. Intelligent Campaign Dashboard

```tsx
// Simple city selector
<CitySelector 
  onSelect={(city, state) => analyzeCoverage(city, state)}
/>

// Coverage analysis display
<CoverageAnalysis
  cityData={cityData}
  coverageStats={coverageStats}
  recommendations={recommendations}
/>

// Campaign plan preview
<CampaignPlanPreview
  plan={campaignPlan}
  onApprove={() => startCampaign()}
  onModify={() => showAdvancedOptions()}
/>

// Real-time progress monitor
<CampaignProgress
  campaign={activeCampaign}
  refreshInterval={5000}
/>
```

### 2. Campaign History View
- List of past campaigns per city
- Visual coverage maps
- Performance metrics
- Export capabilities

---

## Implementation Priority

### Phase 1: Core Intelligence (Week 1-2)
1. ✅ Geocoding service integration
2. ✅ Coverage analyzer
3. ✅ Database schema for campaigns
4. ✅ Industry recommender algorithm
5. ✅ Campaign planner
6. ✅ Basic API endpoints

### Phase 2: Auto-Execution (Week 2-3)
1. ✅ Campaign executor service
2. ✅ Task queue management
3. ✅ Progress tracking
4. ✅ Error handling & retries
5. ✅ Completion notifications

### Phase 3: UI Integration (Week 3-4)
1. ✅ City selector component
2. ✅ Campaign creation wizard
3. ✅ Progress dashboard
4. ✅ Campaign history view

### Phase 4: LLM Enhancement (Week 4+)
1. ⏳ OpenAI integration
2. ⏳ Industry recommendation AI
3. ⏳ Campaign optimization AI
4. ⏳ Insights generation

---

## Key Benefits

### For Users
- **Simplicity**: Just pick a city
- **Confidence**: System ensures complete coverage
- **Efficiency**: No manual work per industry
- **Insights**: Clear reporting on what's been done

### For System
- **Deduplication**: Never scrape same industry/zone twice
- **Optimization**: Intelligent task prioritization
- **Scalability**: Can run multiple campaigns in parallel
- **Reliability**: Built-in error handling and retries

---

## Cost Optimization Strategies

1. **Cooldown Tracking**
   - Don't re-scrape zones within 30 days
   - Use existing coverage_grid cooldown_until

2. **Batch Processing**
   - Group similar searches together
   - Optimize API call patterns

3. **Smart Prioritization**
   - High-value industries first
   - Popular industries in business hubs
   - Low-competition industries in smaller cities

4. **Budget Controls**
   - Hard stop at max_budget
   - Pause/resume capability
   - Cost estimation before execution

---

## Recommended Next Steps

1. **Implement Rule-Based System First** (No LLM needed)
   - Faster to build
   - More predictable
   - Lower ongoing costs
   - Easier to debug

2. **Add Geocoding Service**
   - Use Nominatim (free, open-source)
   - Or Google Geocoding API (paid, more accurate)

3. **Build Campaign Database Schema**
   - Track campaign state
   - Enable resume after failures
   - Historical analysis

4. **Create Intelligent Campaign API**
   - Analyze endpoint
   - Create endpoint
   - Execute endpoint
   - Monitor endpoint

5. **Update Frontend**
   - Simple city selector
   - Campaign wizard
   - Progress dashboard

6. **Consider LLM Enhancement Later**
   - After rule-based system proves stable
   - For advanced optimization
   - For business insights

---

## Example User Flow

```
1. User clicks "Start Intelligent Campaign"
2. Selects "Los Angeles, CA" from dropdown
3. System analyzes:
   ✓ Already scraped: 45/250 industries
   ✓ 205 industries remaining
   ✓ Estimated: 5,125 tasks
   ✓ Cost: ~$2,562.50
4. System recommends: "Start with top 20 high-value industries"
5. Shows plan:
   - Real Estate Agents (25 zones)
   - Law Firms (25 zones)
   - Medical Practices (25 zones)
   ... 17 more
   Total: 500 tasks, ~$250
6. User clicks "Approve & Start"
7. System executes automatically
8. User monitors progress in real-time
9. Receives completion notification
10. Reviews 4,500 qualified leads generated
```

---

## Conclusion

**Recommended Approach**: Start with **Rule-Based Intelligence** (Option 1)

This provides 90% of the value with:
- ✅ Minimal complexity
- ✅ Predictable behavior
- ✅ Low ongoing costs
- ✅ Easy maintenance

Enhance with LLM later for:
- Advanced industry recommendations
- Market insights
- Strategy optimization

The key is letting the system handle all the complexity while giving users simple, powerful control.

