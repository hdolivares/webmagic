# Hunter Module

The Hunter module is responsible for scraping Google My Business listings, filtering qualified leads, and storing them in the database.

## Components

### 1. Outscraper Client (`scraper.py`)
Wrapper for the Outscraper API that handles:
- Searching businesses by location and industry
- Fetching business details by Place ID
- Data normalization from Outscraper format to our schema
- Error handling and rate limiting

**Usage:**
```python
from services.hunter.scraper import OutscraperClient

scraper = OutscraperClient()
businesses = await scraper.search_businesses(
    query="Plumbers",
    city="Austin",
    state="TX",
    limit=50
)
```

### 2. Lead Qualifier (`filters.py`)
Qualification and filtering logic for leads:
- Scores businesses 0-100 based on multiple criteria
- Filters out chains/franchises
- Identifies businesses without websites (primary target)
- Rewards high ratings and review counts
- Extracts emails from reviews when possible

**Scoring System:**
- No website: +30 points
- Has email: +25 points
- High rating (4.5+): +20 points
- Many reviews (50+): +15 points
- Local business (not chain): +10 points

**Usage:**
```python
from services.hunter.filters import LeadQualifier

qualifier = LeadQualifier(min_score=50, require_no_website=True)
qualified = qualifier.filter_batch(businesses)
stats = qualifier.get_statistics(businesses)
```

### 3. Business Service (`business_service.py`)
Database operations for businesses:
- CRUD operations (create, read, update, delete)
- Bulk creation (optimized for scraping)
- Filtering and pagination
- Statistics and analytics
- Duplicate detection

**Usage:**
```python
from services.hunter.business_service import BusinessService

service = BusinessService(db)

# Create business
business = await service.create_business(business_data)

# List with filters
businesses, total = await service.list_businesses(
    skip=0,
    limit=50,
    filters={"website_status": "none", "rating__gte": 4.0}
)

# Get stats
stats = await service.get_stats()
```

### 4. Coverage Grid Service (`coverage_service.py`)
Manages scraping territories (city + industry combinations):
- Tracks which locations have been scraped
- Priority-based target selection
- Status management (pending, in_progress, completed, cooldown)
- Cooldown periods to avoid re-scraping too soon
- Metrics tracking (leads, qualified, conversions)

**Usage:**
```python
from services.hunter.coverage_service import CoverageService

service = CoverageService(db)

# Get or create coverage
coverage, created = await service.get_or_create_coverage(
    state="TX",
    city="Austin",
    industry="Coffee Shop"
)

# Get next target to scrape
targets = await service.get_next_target(limit=1)

# Mark as completed
await service.mark_completed(
    coverage.id,
    lead_count=50,
    qualified_count=15,
    cooldown_hours=168  # 7 days
)
```

### 5. Hunter Service (`hunter_service.py`)
Main orchestration service that coordinates the entire scraping workflow:
- Scrapes businesses using Outscraper
- Filters and qualifies leads
- Saves to database
- Updates coverage grid
- Provides comprehensive reporting

**Usage:**
```python
from services.hunter.hunter_service import HunterService

hunter = HunterService(db)

# Scrape specific location
result = await hunter.scrape_location(
    city="Austin",
    state="TX",
    industry="Plumbers",
    limit=50
)

# Scrape next priority target
result = await hunter.scrape_next_target(limit=50)

# Get report
report = await hunter.get_scraping_report()
```

## API Endpoints

### Businesses
- `GET /api/v1/businesses/` - List businesses with filters
- `GET /api/v1/businesses/stats` - Get business statistics
- `GET /api/v1/businesses/{id}` - Get single business
- `PATCH /api/v1/businesses/{id}` - Update business
- `DELETE /api/v1/businesses/{id}` - Delete business

### Coverage & Scraping
- `GET /api/v1/coverage/` - List coverage entries
- `GET /api/v1/coverage/stats` - Get coverage statistics
- `GET /api/v1/coverage/next-target` - Get next scraping target
- `GET /api/v1/coverage/{id}` - Get single coverage entry
- `POST /api/v1/coverage/` - Create coverage entry
- `PATCH /api/v1/coverage/{id}` - Update coverage entry
- `POST /api/v1/coverage/scrape` - Trigger scraping (background)
- `POST /api/v1/coverage/scrape-next` - Scrape next target (sync)
- `GET /api/v1/coverage/report/scraping` - Get scraping report

## Workflow

1. **Create or Select Target**: Coverage grid entry with location + industry
2. **Mark In Progress**: Set status to prevent concurrent scraping
3. **Scrape**: Call Outscraper API to get businesses
4. **Qualify**: Filter and score leads based on criteria
5. **Save**: Bulk insert qualified businesses to database
6. **Update Coverage**: Mark complete, set cooldown, update metrics
7. **Report**: Return results with statistics

## Testing

Run the Phase 2 test script:

```bash
cd backend
python test_phase2.py
```

This will:
- Test authentication
- Get initial statistics
- Create coverage entry
- (Optionally) Run actual scrape
- Display results and reports

## Configuration

Required environment variables:
- `OUTSCRAPER_API_KEY` - Get from https://app.outscraper.com
- `DATABASE_URL` - Supabase PostgreSQL connection string

## Next Steps

- [ ] Add Celery tasks for async scraping
- [ ] Implement autopilot conductor script
- [ ] Add email extraction from websites
- [ ] Implement scraping scheduler
- [ ] Add webhooks for scraping completion
