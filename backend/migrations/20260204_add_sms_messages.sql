-- Migration: Add SMS Messages table for inbox functionality
-- Date: 2026-02-04
-- Description: Stores all SMS messages (inbound and outbound) for inbox view

-- Create SMS messages table
CREATE TABLE IF NOT EXISTS sms_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Relations (optional - messages can exist without campaign/business)
  campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
  business_id UUID REFERENCES businesses(id) ON DELETE SET NULL,
  
  -- Message details
  direction VARCHAR(10) NOT NULL CHECK (direction IN ('inbound', 'outbound')),
  from_phone VARCHAR(20) NOT NULL,
  to_phone VARCHAR(20) NOT NULL,
  body TEXT NOT NULL,
  
  -- Status tracking
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  -- inbound: received
  -- outbound: pending, queued, sent, delivered, failed
  
  -- Provider tracking
  telnyx_message_id VARCHAR(255),
  
  -- Cost tracking (for outbound)
  segments INTEGER DEFAULT 1,
  cost NUMERIC(10, 4),
  
  -- Error tracking
  error_code VARCHAR(50),
  error_message TEXT,
  
  -- Timestamps
  received_at TIMESTAMP WITH TIME ZONE,  -- When message was received (inbound)
  sent_at TIMESTAMP WITH TIME ZONE,      -- When message was sent (outbound)
  delivered_at TIMESTAMP WITH TIME ZONE, -- When delivery confirmed
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_sms_messages_business ON sms_messages(business_id);
CREATE INDEX IF NOT EXISTS idx_sms_messages_campaign ON sms_messages(campaign_id);
CREATE INDEX IF NOT EXISTS idx_sms_messages_direction ON sms_messages(direction);
CREATE INDEX IF NOT EXISTS idx_sms_messages_status ON sms_messages(status);
CREATE INDEX IF NOT EXISTS idx_sms_messages_from_phone ON sms_messages(from_phone);
CREATE INDEX IF NOT EXISTS idx_sms_messages_to_phone ON sms_messages(to_phone);
CREATE INDEX IF NOT EXISTS idx_sms_messages_created ON sms_messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sms_messages_telnyx_id ON sms_messages(telnyx_message_id);

-- Trigger for updated_at
CREATE TRIGGER update_sms_messages_updated_at
  BEFORE UPDATE ON sms_messages
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE sms_messages IS 'Stores all SMS messages for inbox functionality';
COMMENT ON COLUMN sms_messages.direction IS 'inbound = received from business, outbound = sent to business';
COMMENT ON COLUMN sms_messages.status IS 'Message delivery status';
COMMENT ON COLUMN sms_messages.telnyx_message_id IS 'Telnyx message ID for tracking';

