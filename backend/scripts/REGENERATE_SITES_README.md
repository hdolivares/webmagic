# Regenerating Sites (e.g. Missing Hero / 64k Truncation)

## What happened

If a generated site is missing the hero (or other top-of-page content), the model response was likely **truncated at the 64k token limit**. The architect agent uses `max_tokens=64000`; when the response hits that limit, the tail (or part of the HTML) is cut off.

## Best way: full pipeline re-generation

The **recommended approach** is to re-run the **full architect process** (Analyst → Concept → Art Director → Architect) for the affected sites:

1. **Same quality** – All stages run again with current prompts and model.
2. **No schema dependency** – We don’t need stored `analysis` / `creative_dna` on the site (only `design_brief` is on `generated_sites`; analyst/concept outputs are not persisted for architect-only re-runs).
3. **Already supported** – The Celery task `generate_site_for_business`:
   - Finds the existing site by `business_id`
   - If status is `"completed"` but HTML fails the quality check (e.g. `_is_html_complete`: hero/nav in first 2k chars, min ~20k bytes), it marks the site as `failed` and **re-runs the full pipeline**, reusing the same **subdomain**.

So you only need to **queue the generation task** for the right `business_id`. The task handles “completed but broken” and regenerates.

## Script: regenerate by subdomain

Use the script that looks up `business_id` from subdomain and queues the task:

```bash
# From repo root (with backend on PYTHONPATH or run from backend)
python backend/scripts/regenerate_sites_by_subdomain.py

# Or pass subdomains explicitly
python backend/scripts/regenerate_sites_by_subdomain.py florence-pet-clinic-1771107215496-f85c9b01 nyc-plumbing-heating-drain-cleaning-1770270516683-fe955ad3
```

Defaults (if no args) are the two known broken sites:

- `florence-pet-clinic-1771107215496-f85c9b01`
- `nyc-plumbing-heating-drain-cleaning-1770270516683-fe955ad3`

The script queues `generate_site_for_business` on the `generation` queue. Workers will run the full pipeline and update the same site record (same URL).

## Optional: architect-only regeneration (future)

To re-run **only the Architect** (faster, fewer tokens), you’d need:

1. **Stored inputs** – `generated_sites` (or a related table) would need to persist:
   - `analysis`
   - `creative_dna` (concept output)
   - (already have `design_brief`)
2. **API or script** – Load site by subdomain, build `previous_results` from DB, call `orchestrator.regenerate_stage("code", ...)`, then update site `html_content` / `css_content` / `js_content`.

Today we don’t persist analyst/concept outputs on the site, so **full pipeline regeneration** is the supported and correct approach.

## Reducing future truncation

- **Prompt** – In the architect prompt, you can ask for “HTML first, hero section at the very start” so truncation is more likely to cut the end (e.g. footer) than the hero.
- **Max tokens** – Already at 64k; no increase without model support.
- **Chunking** – A larger change would be to have the architect output in chunks (e.g. hero + sections) and merge; that would require prompt and parsing changes.
