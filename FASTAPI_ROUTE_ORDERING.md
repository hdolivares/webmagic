# FastAPI Route Ordering Best Practices

## Critical Rule: Specific Routes BEFORE Generic Routes

FastAPI matches routes in the **order they are defined**. Once a match is found, it stops looking and uses that route handler.

## The Problem

If you define a generic route (with path parameters) **before** a specific route (with a literal path), FastAPI will try to match the generic route first and fail with validation errors.

### ❌ INCORRECT Order (Causes 422 Errors)

```python
# Generic route defined FIRST - will match everything!
@router.get("/{business_id}")
async def get_business(business_id: UUID):
    # This will try to match ANY path, including "needs-generation"
    # FastAPI will try to parse "needs-generation" as a UUID
    # Result: 422 Unprocessable Entity
    pass

# Specific route defined AFTER - will NEVER be reached!
@router.get("/needs-generation")
async def get_businesses_needing_generation():
    # This route is unreachable because /{business_id} matches first
    pass
```

**Error you'll see:**
```
ValidationError: 
  'loc': ('path', 'business_id'), 
  'msg': 'Input should be a valid UUID, invalid character: expected an optional prefix of `urn:uuid:` followed by [0-9a-fA-F-], found `n` at 1', 
  'input': 'needs-generation'
```

### ✅ CORRECT Order

```python
# Specific routes FIRST
@router.get("/stats")
async def get_stats():
    pass

@router.get("/needs-generation")
async def get_businesses_needing_generation():
    pass

@router.get("/filters/quick")
async def get_quick_filters():
    pass

# Generic routes with path parameters LAST
@router.get("/{business_id}")
async def get_business(business_id: UUID):
    # Now this only matches if no specific route matched first
    pass
```

## Route Ordering Checklist

When adding new routes to a FastAPI router, follow this order:

1. **Root route** (`/`)
2. **Specific literal paths** (e.g., `/stats`, `/needs-generation`, `/filters/quick`)
3. **Paths with query parameters only** (e.g., `/search?q=...`)
4. **Paths with specific prefixes** (e.g., `/filters/presets`, `/bulk/export`)
5. **Generic paths with path parameters** (e.g., `/{business_id}`, `/{id}`)
6. **Very generic catch-all routes** (use sparingly!)

## Real-World Example from WebMagic

In `backend/api/v1/businesses.py`, the correct order is:

```python
@router.get("/")                              # Root
@router.get("/stats")                         # Specific: stats
@router.get("/needs-generation")              # Specific: needs-generation
@router.get("/filters/quick")                 # Specific: filters/quick
@router.get("/filters/stats")                 # Specific: filters/stats
@router.get("/filters/presets")               # Specific: filters/presets
@router.get("/{business_id}")                 # Generic: any UUID
@router.delete("/filters/presets/{preset_id}") # Specific prefix, then generic
```

## Debugging Tips

### 1. Enable Detailed Validation Error Logging

Add this to your `main.py`:

```python
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log and handle validation errors with detailed information."""
    logger.error(f"❌ Validation error on {request.method} {request.url.path}")
    logger.error(f"   Errors: {exc.errors()}")
    logger.error(f"   Body: {exc.body if hasattr(exc, 'body') else 'N/A'}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": exc.body if hasattr(exc, 'body') else None},
    )
```

### 2. Check Current Route Order

```bash
# Search for all route decorators in order
grep -n "^@router\.(get|post|put|patch|delete)" backend/api/v1/your_file.py
```

### 3. Test Specific Routes

Use FastAPI's automatic docs at `/docs` to see all registered routes and their order.

## Common Mistakes to Avoid

1. **Adding new specific routes at the end of the file** - Always insert them before generic routes
2. **Forgetting about existing generic routes** - Check for `/{id}`, `/{uuid}`, `/{slug}` patterns
3. **Not testing after adding routes** - Always test the new endpoint immediately
4. **Assuming route order doesn't matter** - It always matters in FastAPI!

## Prevention Strategy

When adding a new route:

1. ✅ Search for existing generic routes with path parameters
2. ✅ Place your new specific route BEFORE any generic routes
3. ✅ Test the endpoint immediately after deployment
4. ✅ Check logs for any 422 errors related to path validation

## Key Takeaway

> **Specific before Generic, Always!**
> 
> If you have a route like `/{id}`, make sure ALL literal paths (like `/stats`, `/export`, `/needs-generation`) are defined BEFORE it.

---

**Last Updated:** February 14, 2026  
**Incident Reference:** Fixed `/needs-generation` route ordering bug that caused 422 errors when trying to match against `/{business_id}` UUID validation.
