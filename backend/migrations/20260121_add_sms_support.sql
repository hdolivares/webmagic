-- Migration: Add SMS support to campaigns
-- Date: 2026-01-21
-- Description: Adds multi-channel campaign support (email + SMS)

-- Add new columns to campaigns table for SMS support
ALTER TABLE campaigns 
  ADD COLUMN IF NOT EXISTS channel VARCHAR(20) DEFAULT 'email' NOT NULL,
  ADD COLUMN IF NOT EXISTS recipient_phone VARCHAR(20),
  ADD COLUMN IF NOT EXISTS sms_body TEXT,
  ADD COLUMN IF NOT EXISTS sms_provider VARCHAR(50),
  ADD COLUMN IF NOT EXISTS sms_sid VARCHAR(255),
  ADD COLUMN IF NOT EXISTS sms_segments INTEGER,
  ADD COLUMN IF NOT EXISTS sms_cost NUMERIC(10, 4);

-- Make recipient_email optional (not all campaigns use email)
ALTER TABLE campaigns ALTER COLUMN recipient_email DROP NOT NULL;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_campaigns_channel ON campaigns(channel);
CREATE INDEX IF NOT EXISTS idx_campaigns_recipient_phone ON campaigns(recipient_phone);
CREATE INDEX IF NOT EXISTS idx_campaigns_sms_sid ON campaigns(sms_sid);

-- Create SMS opt-out tracking table for TCPA compliance
CREATE TABLE IF NOT EXISTS sms_opt_outs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone_number VARCHAR(20) UNIQUE NOT NULL,
  opted_out_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  source VARCHAR(50) NOT NULL,  -- 'reply_stop', 'manual', 'complaint', 'admin'
  campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
  notes TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for opt-out lookups
CREATE INDEX IF NOT EXISTS idx_sms_opt_outs_phone ON sms_opt_outs(phone_number);
CREATE INDEX IF NOT EXISTS idx_sms_opt_outs_opted_out_at ON sms_opt_outs(opted_out_at);

-- Add trigger for updated_at on sms_opt_outs
CREATE TRIGGER update_sms_opt_outs_updated_at
  BEFORE UPDATE ON sms_opt_outs
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE sms_opt_outs IS 'Tracks phone numbers that have opted out of SMS campaigns for TCPA compliance';
COMMENT ON COLUMN campaigns.channel IS 'Campaign channel: email, sms, whatsapp, voice';
COMMENT ON COLUMN campaigns.sms_cost IS 'Actual cost in USD for SMS delivery';
COMMENT ON COLUMN sms_opt_outs.source IS 'How the opt-out was initiated: reply_stop, manual, complaint, admin';

