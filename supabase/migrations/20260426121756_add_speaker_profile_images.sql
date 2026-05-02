ALTER TABLE speakers
ADD COLUMN IF NOT EXISTS profile_image_url TEXT,
ADD COLUMN IF NOT EXISTS profile_image_source TEXT,
ADD COLUMN IF NOT EXISTS profile_image_license TEXT,
ADD COLUMN IF NOT EXISTS profile_image_updated_at TIMESTAMPTZ;
