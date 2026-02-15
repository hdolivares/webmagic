#!/bin/bash
# Test LLM validation with CORRECT data extraction
# This tests if the LLM will make the right decision when given proper Playwright data

echo "=========================================="
echo "Testing LLM Validation Fix"
echo "=========================================="
echo ""
echo "Business: Oren Hen EA, Inc."
echo "URL: http://orenhenea.com/"
echo ""
echo "BEFORE FIX: LLM said 'No contact information'"
echo "AFTER FIX: Testing with correct Playwright data..."
echo ""

# Read API key from .env file
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | grep ANTHROPIC_API_KEY | xargs)
fi

# Test with CORRECT data (Playwright returns flat structure, not nested)
curl -X POST https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-3-haiku-20240307",
    "max_tokens": 1000,
    "temperature": 0,
    "messages": [{
      "role": "user",
      "content": "You are an expert website validation specialist. Your job is to determine if a website truly belongs to a specific business.\n\nBUSINESS INFORMATION:\n- Name: Oren Hen EA, Inc.\n- Phone: +1 323-433-4363\n- Email: Not provided\n- Address: Not provided\n- City: Los Angeles, State: California\n- Country: US\n\nWEBSITE INFORMATION:\n- URL: http://orenhenea.com/\n- Final URL (after redirects): http://orenhenea.com/\n- Title: Los Angeles & Los Angeles, CA Enrolled Agent Firm | Home Page | Oren Hen EA, Inc.\n- Meta Description: Take a look at our Home page. Oren Hen EA, Inc. is a full service tax, accounting and business consulting firm located in Los Angeles, CA.\n- Phones found: 310-246-1532, 323-433-4363\n- Emails found: info@orenhenea.com\n- Has address: true\n- Has business hours: false\n- Content preview (first 500 chars): E: info@orenhenea.com / T: 323-433-4363\nClient Portal Login\nSubscribe\nHome\nAbout\nServices\nNewsletter\nGuides\nTax Center\nResources\nContact\nOnline Payments\nClient Reviews\nProviding the support you deserve.\n1\n2\n3\n4\nWhere'\''s My Refund?\nWhen will you receive your refund? The answer depends on how you filed your return. The IRS should issue your refund check within six to eight weeks of filing a paper return.\nOur Newsletter\nMiss last month'\''s newsletter? No problem. We keep the last 6 months of n\n- Word count: 405\n\nINVALID WEBSITE TYPES (mark as \"missing\" - business needs a real website):\n\n1. MEMBER DIRECTORIES & LISTINGS:\n   - Chamber of Commerce member pages\n   - Better Business Bureau profiles\n   - Trade association member directories\n   \n2. AGGREGATOR & REVIEW SITES:\n   - Yelp, Yellow Pages, White Pages\n   - Google Maps/Business profiles\n   - MapQuest business listings\n   \n3. SOCIAL MEDIA PROFILES:\n   - Facebook pages\n   - LinkedIn company pages\n   - Instagram profiles\n\n4. PLACEHOLDER/UNRELATED:\n   - Under construction pages\n   - Coming soon pages\n   - Domain parking pages\n   - Completely unrelated businesses\n\nCROSS-REFERENCE RULES:\n✅ STRONG MATCH SIGNALS:\n- Phone number matches exactly or partially (same area code + first 6 digits)\n- Business name appears prominently in title or main content\n- Address street name or zip code matches\n- Multiple contact methods match (phone + email, phone + address)\n\n⚠️ WEAK SIGNALS:\n- Business name in URL domain\n- Generic services match (plumbing, heating)\n- Same city/state (not enough alone)\n\n❌ MISMATCH SIGNALS:\n- Phone numbers are completely different\n- Business name does not appear anywhere\n- Wrong city/state mentioned prominently\n- Website clearly belongs to different business\n\nVALIDATION DECISION:\nRespond ONLY with valid JSON in this exact format:\n{\n  \"verdict\": \"valid\" | \"invalid\" | \"missing\",\n  \"confidence\": 0.0-1.0,\n  \"reasoning\": \"Concise explanation of your decision (2-3 sentences)\",\n  \"recommendation\": \"keep_url\" | \"clear_url_and_mark_missing\" | \"mark_invalid_keep_url\",\n  \"match_signals\": {\n    \"phone_match\": true/false,\n    \"address_match\": true/false,\n    \"name_match\": true/false,\n    \"is_directory\": true/false,\n    \"is_aggregator\": true/false\n  }\n}\n\nVERDICT DEFINITIONS:\n- \"valid\": This IS the business actual website (even if low quality)\n- \"invalid\": This IS their website but broken/placeholder (keep URL for records)\n- \"missing\": NOT their website (directory/aggregator/unrelated) - clear URL\n\nNow analyze the provided business and website information above and return your validation decision."
    }]
  }' | python3 -m json.tool

echo ""
echo "=========================================="
echo "Expected: verdict=valid, phone_match=true, name_match=true"
echo "=========================================="

