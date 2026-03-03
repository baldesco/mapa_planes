-- Add description column to places if missing
ALTER TABLE places ADD COLUMN IF NOT EXISTS description TEXT;

-- Add is_main column to visit_photos if missing
ALTER TABLE visit_photos ADD COLUMN IF NOT EXISTS is_main BOOLEAN DEFAULT FALSE;

-- Optional: Mark the oldest photo as main if none are set
UPDATE visit_photos
SET is_main = TRUE
WHERE id IN (
    SELECT MIN(id)
    FROM visit_photos
    GROUP BY visit_id
) AND NOT EXISTS (
    SELECT 1 FROM visit_photos vp2 
    WHERE vp2.visit_id = visit_photos.visit_id AND vp2.is_main = TRUE
);

-- Update the main visit table for backward compatibility
UPDATE visits v
SET image_url = (
    SELECT image_url 
    FROM visit_photos vp 
    WHERE vp.visit_id = v.id AND vp.is_main = TRUE
    LIMIT 1
)
WHERE v.image_url IS NULL;