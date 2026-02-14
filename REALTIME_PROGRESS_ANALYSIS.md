# Real-Time Progress Tracking - Analysis & Implementation Plan

**Date:** February 14, 2026  
**Current Status:** Synchronous scraping (frontend waits for completion)  
**Proposed:** Asynchronous scraping with real-time progress updates

---

## Current Architecture Issues

### 1. **Synchronous Scraping (Blocking)**

**Current Flow:**
```
User clicks "Start Scraping" 
  ↓
Frontend sends POST /api/v1/intelligent-campaigns/scrape-zone
  ↓
Backend starts scraping (3-5 minutes)
  ├─ Outscraper API call (30s)
  ├─ HTTP validation (25s)
  ├─ ScrapingDog + LLM verification (75s + rate limiting)
  ├─ Database saves (15s)
  ↓
Backend returns complete result
  ↓
Frontend receives response and updates UI
```

**Problems:**
- ❌ Frontend is blocked for 3-5 minutes (no feedback)
- ❌ User can't see what's happening
- ❌ If network drops, progress is lost
- ❌ If user closes tab, scraping continues but no visibility
- ❌ 504 timeouts if operation takes >5 minutes

---

### 2. **"Overall Progress" Section**

**What It Shows:**

From `CoveragePage.tsx` lines 184-203:

```typescript
<Card>
  <div className="card-header">
    <h2 className="card-title">Overall Progress</h2>
  </div>
  <div className="progress-bar-wrapper">
    <div className="progress-bar" style={{ width: `${stats?.completion_percentage || 0}%` }}>
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
```

**What It Means:**

This shows **aggregate progress across ALL coverage grids** in your entire discovery campaign:

- **Total Grids:** City × Category combinations (e.g., Los Angeles × plumbers = 1 grid)
- **Completed:** Grids that have been successfully scraped
- **In Progress:** Grids currently being scraped (should be 0 in your image)
- **Pending:** Grids not yet scraped
- **Failed:** Grids that encountered errors
- **Completion %:** `(Completed / Total) × 100`

**Your Image Shows:**
- 44.7% complete
- 21 grids completed
- 0 currently in progress
- 26 pending
- 0 failed
- **Total:** 47 grids (21 + 26)

**Why "0 In Progress":**

The `in_progress_grids` count is only updated in the database during scraping. Since scraping is synchronous and completes before returning, by the time you see the UI, the grid status is already "completed" or "failed", never "in progress".

**To see "In Progress" > 0:**
- Need asynchronous scraping
- Need to query status during active scrapes

---

### 3. **"Overview" Tab is Empty**

**Problem:** Lines 256-278 show the tab navigation, but lines 280-376 only render content for `activeTab === 'locations'` and `activeTab === 'categories'`. There's **no content for `activeTab === 'overview'`**!

```typescript
{/* Tabs */}
<div className="tabs-container">
  <div className="tabs">
    <button onClick={() => setActiveTab('overview')} className={`tab ${activeTab === 'overview' ? 'tab-active' : ''}`}>
      Overview
    </button>
    <button onClick={() => setActiveTab('locations')}>
      Locations ({locations.length})
    </button>
    <button onClick={() => setActiveTab('categories')}>
      Categories ({categories.length})
    </button>
  </div>
</div>

{/* Tab Content */}
{activeTab === 'locations' && (
  <Card>
    {/* Locations table */}
  </Card>
)}

{activeTab === 'categories' && (
  <Card>
    {/* Categories table */}
  </Card>
)}

{/* ❌ NO CONTENT FOR activeTab === 'overview' */}
```

**Solution:** Add an overview section with campaign summary, recent activity, and key metrics.

---

## ✅ Solution: Real-Time Progress Tracking

### Architecture Options

#### **Option 1: Celery Background Tasks + Polling (RECOMMENDED)**

**How It Works:**

```
User clicks "Start Scraping"
  ↓
Frontend sends POST /scrape-zone
  ↓
Backend queues Celery task, returns task_id immediately
  ↓
Frontend receives task_id in <1 second
  ↓
Frontend polls GET /scrape-zone/{task_id}/status every 2-3 seconds
  ↓
Backend returns current progress:
  {
    "status": "in_progress",
    "progress": {
      "current_step": "ScrapingDog verification",
      "businesses_processed": 15,
      "total_businesses": 48,
      "percent_complete": 31,
      "eta_seconds": 120
    }
  }
  ↓
Frontend updates progress bar in real-time
  ↓
When status = "completed", show final results
```

**Advantages:**
- ✅ Simple to implement (Celery already set up)
- ✅ Works with current infrastructure
- ✅ No WebSocket complexity
- ✅ Survives page refresh (task_id in URL)
- ✅ Can scale to background batch processing

**Implementation Complexity:** 🟢 Low (2-3 hours)

---

#### **Option 2: WebSockets (Server-Sent Events)**

**How It Works:**

```
User clicks "Start Scraping"
  ↓
Frontend opens WebSocket connection
  ↓
Backend starts scraping and pushes updates:
  - "Started Outscraper API call..."
  - "Found 48 businesses from Google Maps"
  - "Validating business #1/48..."
  - "Running LLM verification..."
  - "Progress: 50% complete"
  ↓
Frontend receives real-time updates
  ↓
Backend closes connection when complete
```

**Advantages:**
- ✅ True real-time (instant updates)
- ✅ No polling overhead
- ✅ Can push logs/events as they happen

**Disadvantages:**
- ❌ More complex to implement
- ❌ Requires WebSocket infrastructure
- ❌ Harder to debug
- ❌ Doesn't survive page refresh easily

**Implementation Complexity:** 🟡 Medium (6-8 hours)

---

#### **Option 3: Server-Sent Events (SSE)**

**How It Works:**

Similar to WebSockets but simpler (one-way communication from server to client).

```
User clicks "Start Scraping"
  ↓
Frontend opens SSE connection to /scrape-zone/{task_id}/stream
  ↓
Backend streams events:
  event: progress
  data: {"step": "Outscraper", "percent": 10}

  event: progress
  data: {"step": "HTTP validation", "percent": 40}

  event: complete
  data: {"results": {...}}
  ↓
Frontend receives events and updates UI
```

**Advantages:**
- ✅ Simpler than WebSockets
- ✅ Built into browsers (EventSource API)
- ✅ Automatic reconnection
- ✅ True real-time updates

**Disadvantages:**
- ❌ One-way only (server → client)
- ❌ Requires FastAPI SSE support
- ❌ Slightly more complex than polling

**Implementation Complexity:** 🟡 Medium (4-6 hours)

---

### ✅ RECOMMENDED: Option 1 (Celery + Polling)

**Why This Is Best:**

1. **Already Have Infrastructure:** Celery is set up for validation tasks
2. **Simple to Implement:** Standard REST endpoints
3. **Reliable:** Survives page refreshes, network issues
4. **Scalable:** Can handle batch processing easily
5. **Debuggable:** Easy to trace task status in Redis/logs

---

## Implementation Plan

### Phase 1: Backend - Celery Task for Scraping

**File:** `backend/tasks/scraping_tasks.py` (NEW)

```python
"""
Celery tasks for asynchronous scraping with progress tracking.
"""
from celery import Task
from celery_app import celery_app
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class ScrapeProgressTask(Task):
    """
    Base task class with progress tracking.
    
    Stores progress in Redis for real-time status queries.
    """
    
    def update_progress(
        self,
        current_step: str,
        businesses_processed: int,
        total_businesses: int,
        details: Dict[str, Any] = None
    ):
        """Update task progress in Redis."""
        percent_complete = int((businesses_processed / total_businesses) * 100) if total_businesses > 0 else 0
        
        self.update_state(
            state='PROGRESS',
            meta={
                'current_step': current_step,
                'businesses_processed': businesses_processed,
                'total_businesses': total_businesses,
                'percent_complete': percent_complete,
                'details': details or {}
            }
        )


@celery_app.task(bind=True, base=ScrapeProgressTask)
def scrape_zone_async(
    self,
    strategy_id: str,
    city: str,
    state: str,
    category: str,
    limit_per_zone: int = 50
) -> Dict[str, Any]:
    """
    Asynchronously scrape a zone with progress tracking.
    
    Args:
        strategy_id: UUID of the geo strategy
        city: City name
        state: State code
        category: Business category
        limit_per_zone: Max businesses per zone
        
    Returns:
        Scrape results with business data
    """
    from core.database import get_db_session_sync
    from services.hunter.hunter_service import HunterService
    
    logger.info(f"Starting async scrape for {category} in {city}, {state}")
    
    try:
        # Update: Starting
        self.update_progress(
            current_step="Initializing scrape",
            businesses_processed=0,
            total_businesses=limit_per_zone
        )
        
        with get_db_session_sync() as db:
            hunter_service = HunterService(db)
            
            # We'll need to modify hunter_service to accept a progress callback
            # For now, just run the scrape
            result = await hunter_service.scrape_with_intelligent_strategy(
                city=city,
                state=state,
                category=category,
                limit_per_zone=limit_per_zone,
                progress_callback=lambda step, processed, total: self.update_progress(
                    current_step=step,
                    businesses_processed=processed,
                    total_businesses=total
                )
            )
            
            logger.info(f"Scrape complete: {result['results']['total_saved']} businesses saved")
            
            return {
                'status': 'completed',
                'result': result
            }
            
    except Exception as e:
        logger.error(f"Scraping task failed: {e}", exc_info=True)
        self.update_state(
            state='FAILURE',
            meta={
                'error': str(e),
                'error_type': type(e).__name__
            }
        )
        raise


@celery_app.task(bind=True)
def batch_scrape_strategy_async(
    self,
    strategy_id: str,
    max_zones: int = None,
    limit_per_zone: int = 50
) -> Dict[str, Any]:
    """
    Scrape multiple zones in sequence with progress tracking.
    
    Args:
        strategy_id: UUID of the geo strategy
        max_zones: Maximum zones to scrape (None = all)
        limit_per_zone: Max businesses per zone
        
    Returns:
        Batch scrape summary
    """
    from core.database import get_db_session_sync
    from services.hunter.hunter_service import HunterService
    
    logger.info(f"Starting batch scrape for strategy {strategy_id}")
    
    try:
        with get_db_session_sync() as db:
            hunter_service = HunterService(db)
            
            result = await hunter_service.scrape_all_zones_for_strategy(
                strategy_id=strategy_id,
                limit_per_zone=limit_per_zone,
                max_zones=max_zones
            )
            
            return result
            
    except Exception as e:
        logger.error(f"Batch scraping task failed: {e}", exc_info=True)
        raise
```

---

### Phase 2: Backend - API Endpoints for Task Status

**File:** `backend/api/v1/intelligent_campaigns.py` (MODIFY)

```python
# Add new imports
from celery.result import AsyncResult
from tasks.scraping_tasks import scrape_zone_async, batch_scrape_strategy_async

# NEW: Response model for task creation
class ScrapeTaskResponse(BaseModel):
    task_id: str
    status: str
    message: str
    strategy_id: str

# NEW: Response model for task status
class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # "pending", "progress", "completed", "failed"
    progress: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# MODIFY: Existing scrape-zone endpoint to be async
@router.post("/scrape-zone", response_model=ScrapeTaskResponse)
async def scrape_next_zone(
    request: ScrapeZoneRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Queue a zone scrape task (returns immediately).
    
    Returns a task_id that can be used to poll for progress.
    """
    try:
        geo_strategy_service = GeoStrategyService(db)
        
        # Get strategy
        strategy = await geo_strategy_service.get_strategy_by_id(request.strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Queue Celery task (returns immediately)
        task = scrape_zone_async.delay(
            strategy_id=request.strategy_id,
            city=strategy.city,
            state=strategy.state,
            category=strategy.category,
            limit_per_zone=request.limit_per_zone
        )
        
        logger.info(f"Queued scrape task {task.id} for strategy {request.strategy_id}")
        
        return ScrapeTaskResponse(
            task_id=task.id,
            status="queued",
            message=f"Scraping task queued for {strategy.city}, {strategy.state}",
            strategy_id=request.strategy_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to queue scrape task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# NEW: Task status endpoint
@router.get("/scrape-zone/{task_id}/status", response_model=TaskStatusResponse)
async def get_scrape_task_status(
    task_id: str,
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get the status of a scraping task.
    
    Poll this endpoint every 2-3 seconds to get real-time progress.
    """
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        
        if task_result.state == 'PENDING':
            return TaskStatusResponse(
                task_id=task_id,
                status="pending",
                progress=None
            )
        
        elif task_result.state == 'PROGRESS':
            return TaskStatusResponse(
                task_id=task_id,
                status="in_progress",
                progress=task_result.info  # Contains current_step, percent_complete, etc.
            )
        
        elif task_result.state == 'SUCCESS':
            return TaskStatusResponse(
                task_id=task_id,
                status="completed",
                result=task_result.result
            )
        
        elif task_result.state == 'FAILURE':
            return TaskStatusResponse(
                task_id=task_id,
                status="failed",
                error=str(task_result.info)
            )
        
        else:
            return TaskStatusResponse(
                task_id=task_id,
                status=task_result.state.lower()
            )
            
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

### Phase 3: Frontend - Polling & Progress UI

**File:** `frontend/src/components/coverage/IntelligentCampaignPanel.tsx` (MODIFY)

```typescript
// Add new state for task tracking
const [taskId, setTaskId] = useState<string | null>(null)
const [progress, setProgress] = useState<{
  current_step: string
  businesses_processed: number
  total_businesses: number
  percent_complete: number
} | null>(null)

// Modified scrape handler
const handleScrapeNextZone = async () => {
  if (!strategy) return
  
  setLoading(true)
  setError(null)
  setProgress(null)
  
  try {
    console.log('🔵 Starting zone scrape...')
    
    // Step 1: Queue the task (returns immediately)
    const response = await api.scrapeZone(strategy.strategy_id, draftMode, limitPerZone)
    
    const taskId = response.task_id
    setTaskId(taskId)
    
    console.log(`✅ Task queued: ${taskId}`)
    
    // Step 2: Poll for progress
    const pollInterval = setInterval(async () => {
      try {
        const statusResponse = await api.getScrapeTaskStatus(taskId)
        
        if (statusResponse.status === 'in_progress' && statusResponse.progress) {
          // Update progress UI
          setProgress(statusResponse.progress)
          console.log(`⏳ Progress: ${statusResponse.progress.percent_complete}% - ${statusResponse.progress.current_step}`)
        }
        
        else if (statusResponse.status === 'completed') {
          // Task completed!
          clearInterval(pollInterval)
          setTaskId(null)
          setProgress(null)
          setLoading(false)
          
          // Update strategy with results
          setScrapeResult(statusResponse.result)
          
          // Refresh strategy
          const updatedStrategy = await api.getIntelligentStrategy(strategy.strategy_id)
          setStrategy(updatedStrategy)
          
          if (onCampaignUpdate) {
            onCampaignUpdate()
          }
          
          console.log('✅ Scrape completed!')
        }
        
        else if (statusResponse.status === 'failed') {
          // Task failed
          clearInterval(pollInterval)
          setTaskId(null)
          setProgress(null)
          setLoading(false)
          setError(statusResponse.error || 'Scraping failed')
          console.error('❌ Scrape failed:', statusResponse.error)
        }
        
      } catch (pollError) {
        console.error('Polling error:', pollError)
        // Don't stop polling on network errors - might recover
      }
    }, 2000) // Poll every 2 seconds
    
    // Cleanup on unmount
    return () => clearInterval(pollInterval)
    
  } catch (err: any) {
    setError(err.response?.data?.detail || err.message || 'Failed to start scrape')
    setLoading(false)
    console.error('❌ Start error:', err)
  }
}

// Add progress UI
{loading && progress && (
  <div className="scraping-progress-panel">
    <div className="progress-header">
      <h3>🔍 Scraping in Progress...</h3>
      <div className="progress-percentage">{progress.percent_complete}%</div>
    </div>
    
    <div className="progress-bar-container">
      <div 
        className="progress-bar-fill"
        style={{ width: `${progress.percent_complete}%` }}
      />
    </div>
    
    <div className="progress-details">
      <div className="progress-step">
        <strong>Current Step:</strong> {progress.current_step}
      </div>
      <div className="progress-count">
        <strong>Businesses Processed:</strong> {progress.businesses_processed} / {progress.total_businesses}
      </div>
    </div>
    
    <div className="progress-steps-list">
      <div className={progress.percent_complete >= 10 ? 'step-done' : 'step-pending'}>
        ✓ Outscraper API call
      </div>
      <div className={progress.percent_complete >= 40 ? 'step-done' : 'step-pending'}>
        {progress.percent_complete >= 40 ? '✓' : '⏳'} HTTP validation
      </div>
      <div className={progress.percent_complete >= 70 ? 'step-done' : 'step-pending'}>
        {progress.percent_complete >= 70 ? '✓' : '⏳'} ScrapingDog + LLM verification
      </div>
      <div className={progress.percent_complete >= 90 ? 'step-done' : 'step-pending'}>
        {progress.percent_complete >= 90 ? '✓' : '⏳'} Saving to database
      </div>
    </div>
  </div>
)}
```

---

### Phase 4: Modify HunterService for Progress Callbacks

**File:** `backend/services/hunter/hunter_service.py` (MODIFY)

```python
async def scrape_with_intelligent_strategy(
    self,
    city: str,
    state: str,
    category: str,
    country: str = "US",
    limit_per_zone: int = 50,
    center_lat: Optional[float] = None,
    center_lon: Optional[float] = None,
    progress_callback: Optional[Callable] = None  # NEW
) -> Dict[str, Any]:
    """
    Scrape with intelligent strategy with optional progress tracking.
    
    Args:
        progress_callback: Optional callback for progress updates
                           Signature: callback(step: str, processed: int, total: int)
    """
    
    # ... existing code ...
    
    # After getting raw businesses
    raw_businesses = outscraper_client.search_google_maps(...)
    
    if progress_callback:
        progress_callback("Processing businesses", 0, len(raw_businesses))
    
    # Inside the processing loop
    for idx, biz_data in enumerate(raw_businesses):
        business_name = biz_data.get('name', 'Unknown')
        logger.info(f"🔍 [{idx+1}/{len(raw_businesses)}] Processing: {business_name}")
        
        # Update progress every 5 businesses
        if progress_callback and idx % 5 == 0:
            progress_callback(
                f"Verifying business {idx+1}/{len(raw_businesses)}",
                idx,
                len(raw_businesses)
            )
        
        # ... existing processing ...
    
    # Final progress update
    if progress_callback:
        progress_callback("Scrape complete", len(raw_businesses), len(raw_businesses))
    
    return result
```

---

## Phase 5: Fix Empty "Overview" Tab

**File:** `frontend/src/pages/Coverage/CoveragePage.tsx` (ADD)

Add this after line 279 (before the locations tab content):

```typescript
{/* Overview Tab Content */}
{activeTab === 'overview' && (
  <div className="overview-grid">
    {/* Campaign Summary */}
    <Card>
      <div className="card-header">
        <h2 className="card-title">Campaign Summary</h2>
      </div>
      <div className="overview-stats">
        <div className="overview-stat">
          <div className="stat-label">Total Coverage Grids</div>
          <div className="stat-value">{stats?.total_grids?.toLocaleString() || '0'}</div>
          <div className="stat-detail">
            {stats?.total_locations || 0} cities × {stats?.total_categories || 0} categories
          </div>
        </div>
        
        <div className="overview-stat">
          <div className="stat-label">Discovery Progress</div>
          <div className="stat-value">{stats?.completion_percentage?.toFixed(1) || '0'}%</div>
          <div className="stat-detail">
            {stats?.completed_grids || 0} of {stats?.total_grids || 0} complete
          </div>
        </div>
        
        <div className="overview-stat">
          <div className="stat-label">Businesses Discovered</div>
          <div className="stat-value text-success">
            {stats?.total_businesses_found?.toLocaleString() || '0'}
          </div>
          <div className="stat-detail">
            Across all locations and categories
          </div>
        </div>
        
        <div className="overview-stat">
          <div className="stat-label">Campaign Cost</div>
          <div className="stat-value">${stats?.actual_cost?.toFixed(2) || '0.00'}</div>
          <div className="stat-detail">
            ${stats?.estimated_cost?.toFixed(2) || '0.00'} estimated total
          </div>
        </div>
      </div>
    </Card>
    
    {/* Top Locations */}
    <Card>
      <div className="card-header">
        <h2 className="card-title">Top Locations</h2>
      </div>
      <div className="overview-list">
        {locations.slice(0, 5).map((loc) => (
          <div key={loc.location} className="overview-list-item">
            <div className="item-main">
              <div className="item-name">{loc.location}, {loc.state}</div>
              <div className="item-meta">
                {loc.total_businesses?.toLocaleString() || '0'} businesses found
              </div>
            </div>
            <div className="item-progress">
              <div className="progress-bar-tiny">
                <div 
                  className="progress-fill"
                  style={{ width: `${loc.completion_percentage || 0}%` }}
                />
              </div>
              <span className="progress-text-small">
                {loc.completion_percentage?.toFixed(0) || '0'}%
              </span>
            </div>
          </div>
        ))}
      </div>
    </Card>
    
    {/* Top Categories */}
    <Card>
      <div className="card-header">
        <h2 className="card-title">Top Categories</h2>
      </div>
      <div className="overview-list">
        {categories.slice(0, 5).map((cat) => (
          <div key={cat.category} className="overview-list-item">
            <div className="item-main">
              <div className="item-name capitalize">{cat.category}</div>
              <div className="item-meta">
                {cat.total_businesses?.toLocaleString() || '0'} businesses · 
                Avg {cat.avg_businesses_per_location?.toFixed(1) || '0'} per location
              </div>
            </div>
            <div className="item-progress">
              <div className="progress-bar-tiny">
                <div 
                  className="progress-fill"
                  style={{ width: `${cat.completion_percentage || 0}%` }}
                />
              </div>
              <span className="progress-text-small">
                {cat.completion_percentage?.toFixed(0) || '0'}%
              </span>
            </div>
          </div>
        ))}
      </div>
    </Card>
    
    {/* Quick Stats */}
    <Card>
      <div className="card-header">
        <h2 className="card-title">Status Breakdown</h2>
      </div>
      <div className="status-breakdown">
        <div className="status-item status-completed">
          <div className="status-count">{stats?.completed_grids || 0}</div>
          <div className="status-label">Completed</div>
        </div>
        <div className="status-item status-in-progress">
          <div className="status-count">{stats?.in_progress_grids || 0}</div>
          <div className="status-label">In Progress</div>
        </div>
        <div className="status-item status-pending">
          <div className="status-count">{stats?.pending_grids || 0}</div>
          <div className="status-label">Pending</div>
        </div>
        <div className="status-item status-failed">
          <div className="status-count">{stats?.failed_grids || 0}</div>
          <div className="status-label">Failed</div>
        </div>
      </div>
    </Card>
  </div>
)}
```

---

## Summary

### Current Issues:
1. ❌ **Synchronous scraping** - Frontend blocked for 3-5 minutes
2. ❌ **No progress visibility** - User sees nothing until completion
3. ❌ **"Overview" tab empty** - No content rendered
4. ❌ **"In Progress" always 0** - No async tracking

### Proposed Solution:
1. ✅ **Celery async tasks** - Background scraping with progress tracking
2. ✅ **Polling API** - Frontend polls for status every 2 seconds
3. ✅ **Real-time progress UI** - Shows current step, percentage, ETA
4. ✅ **Overview tab content** - Campaign summary and top performers
5. ✅ **Progress callbacks** - HunterService updates task state

### Implementation Time:
- **Backend (Celery + API):** 3-4 hours
- **Frontend (Polling + UI):** 2-3 hours
- **Testing:** 1-2 hours
- **Total:** 6-9 hours

### Benefits:
- ✅ No more timeout errors (task runs in background)
- ✅ User can see progress in real-time
- ✅ Can close tab and come back (task_id in URL)
- ✅ Better UX with step-by-step feedback
- ✅ Scalable to batch processing

---

**Next Steps:**

1. Implement Celery scraping task with progress tracking
2. Add task status API endpoints
3. Update frontend to poll for progress
4. Add Overview tab content
5. Test with real scrapes
6. Deploy and monitor

Would you like me to implement this?
