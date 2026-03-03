-- Add description column to places table
ALTER TABLE places ADD COLUMN IF NOT EXISTS description TEXT;
