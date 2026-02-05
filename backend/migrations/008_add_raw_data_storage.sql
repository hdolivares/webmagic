-- Migration 008: Add raw data storage for Outscraper responses
-- This allows us to reprocess data without wasting API credits

-- Add raw_data JSONB column to businesses table
ALTER TABLE businesses 
ADD COLUMN IF NOT EXISTS raw_data JSONB;

-- Add index for faster JSON queries
CREATE INDEX IF NOT EXISTS idx_businesses_raw_data_gin 
ON businesses USING gin (raw_data);

-- Add comment
COMMENT ON COLUMN businesses.raw_data IS 'Full raw JSON response from Outscraper API for data recovery and reprocessing';

