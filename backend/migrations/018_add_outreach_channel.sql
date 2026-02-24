-- Migration 018: Add outreach_channel and phone_validated_at for post-triple-validation phone check
-- Businesses with no website (triple-validated) get phone validation; outcome: sms | email | call_later.
-- call_later = no valid SMS and no email; saved for future generate-website + call flow.

ALTER TABLE businesses
ADD COLUMN IF NOT EXISTS outreach_channel VARCHAR(20) NULL,
ADD COLUMN IF NOT EXISTS phone_validated_at TIMESTAMP NULL;

CREATE INDEX IF NOT EXISTS idx_businesses_outreach_channel ON businesses(outreach_channel);

COMMENT ON COLUMN businesses.outreach_channel IS
'Set by phone validation job: sms (SMS-capable phone), email (has email), call_later (no valid SMS, no email - for future calling).';
COMMENT ON COLUMN businesses.phone_validated_at IS
'When phone validation was last run for this business (triple-validated, pre-generation).';
