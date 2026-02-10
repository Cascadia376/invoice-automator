-- Add missing Stellar configuration columns to stores table
ALTER TABLE stores ADD COLUMN IF NOT EXISTS organization_id TEXT;
ALTER TABLE stores ADD COLUMN IF NOT EXISTS stellar_tenant TEXT;
ALTER TABLE stores ADD COLUMN IF NOT EXISTS stellar_location_id TEXT;
ALTER TABLE stores ADD COLUMN IF NOT EXISTS stellar_location_name TEXT;
ALTER TABLE stores ADD COLUMN IF NOT EXISTS stellar_enabled BOOLEAN DEFAULT FALSE;

-- Backfill organization_id for existing stores
UPDATE stores SET organization_id = 'dev-org' WHERE organization_id IS NULL;
