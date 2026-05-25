CREATE TABLE IF NOT EXISTS home_section_snapshot (
    section_key      text PRIMARY KEY,
    payload          jsonb NOT NULL,
    calculated_at    timestamptz NOT NULL DEFAULT now(),
    expires_at       timestamptz,
    version          integer NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_speeches_recent_member
ON speeches (date DESC, speech_number DESC)
WHERE speaker_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_speeches_speaker_date_order
ON speeches (speaker_id, date ASC, speech_number ASC)
WHERE speaker_id IS NOT NULL;
