-- ============================================================
-- contradiction_candidates
-- ============================================================
CREATE TABLE IF NOT EXISTS contradiction_candidates (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    speaker_id       UUID        NOT NULL REFERENCES speakers (id),
    past_speech_id   UUID        NOT NULL REFERENCES speeches (id),
    recent_speech_id UUID        NOT NULL REFERENCES speeches (id),
    topic_label      TEXT        NOT NULL,
    summary          TEXT        NOT NULL,
    score            FLOAT       NOT NULL DEFAULT 0.0,
    matched_cues     TEXT[]      NOT NULL DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_contradiction_pair UNIQUE (past_speech_id, recent_speech_id)
);

CREATE INDEX IF NOT EXISTS idx_contradiction_speaker_created
ON contradiction_candidates (speaker_id, created_at DESC);
