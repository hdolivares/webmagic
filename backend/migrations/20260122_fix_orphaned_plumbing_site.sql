-- Migration: Fix orphaned plumbing site by creating business record
-- Date: 2026-01-22
-- Description: Create business record for 'la-plumbing-pros' site and link them together

-- Step 1: Create business record for the plumbing company
INSERT INTO businesses (
    id,
    gmb_id,
    name,
    slug,
    email,
    phone,
    address,
    city,
    state,
    zip_code,
    country,
    category,
    subcategory,
    rating,
    review_count,
    website_status,
    contact_status,
    qualification_score,
    scraped_at,
    created_at,
    updated_at
) VALUES (
    gen_random_uuid(),
    NULL,  -- No GMB data since it was manually created
    'Los Angeles Plumbing Pros',
    'la-plumbing-pros-business',
    NULL,  -- Email not captured during test
    '(310) 861-9785',  -- From site title
    NULL,
    'Los Angeles',
    'CA',
    NULL,
    'US',
    'Plumber',
    'Emergency Plumbing',
    NULL,  -- No rating data
    0,
    'generated',  -- Site was already generated
    'pending',    -- Not yet contacted
    75,  -- Decent score since site was generated
    NOW(),
    NOW(),
    NOW()
)
-- Store the ID for the next step
RETURNING id AS business_id;

-- Step 2: Link the existing site to the new business record
-- Note: Replace with actual business_id from Step 1
WITH new_business AS (
    SELECT id FROM businesses WHERE slug = 'la-plumbing-pros-business'
)
UPDATE sites 
SET 
    business_id = (SELECT id FROM new_business),
    updated_at = NOW()
WHERE slug = 'la-plumbing-pros';

-- Step 3: Verify the link was created
SELECT 
    s.slug AS site_slug,
    s.status AS site_status,
    b.name AS business_name,
    b.contact_status,
    b.website_status,
    s.business_id IS NOT NULL AS linked
FROM sites s
LEFT JOIN businesses b ON s.business_id = b.id
WHERE s.slug = 'la-plumbing-pros';

