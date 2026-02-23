-- Create visit_photos table to support multiple photos per visit
CREATE TABLE IF NOT EXISTS visit_photos (
    id BIGSERIAL PRIMARY KEY,
    visit_id BIGINT REFERENCES visits(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    image_url TEXT NOT NULL,
    storage_path TEXT,
    is_main BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_visit_photos_visit_id ON visit_photos(visit_id);

-- Migrate existing image_url from visits to visit_photos (if any)
-- We mark the first photo found for each visit as 'is_main'
INSERT INTO visit_photos (visit_id, user_id, image_url, is_main, created_at)
SELECT id, user_id, image_url, TRUE, created_at
FROM visits
WHERE image_url IS NOT NULL
ON CONFLICT DO NOTHING;

-- NOTE: We keep image_url in visits table for now to avoid breaking changes, 
-- but it can be deprecated/dropped later once the UI/Logic is fully migrated.
