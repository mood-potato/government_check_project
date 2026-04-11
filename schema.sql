-- ============================================================
-- speakers
-- ============================================================
CREATE TABLE speakers (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    mona_code        TEXT        NOT NULL,
    assembly_number  INT         NOT NULL,
    name             TEXT        NOT NULL,
    political_party  TEXT        NOT NULL,
    election_district TEXT,                 -- 비례대표는 NULL 허용
    election_type    TEXT,                  -- 지역구 / 비례대표
    reelection_count INT,                   -- "4선" → 4
    gender           TEXT,
    birth_date       DATE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_speakers_mona_assembly UNIQUE (mona_code, assembly_number)
);

-- TODO: 인덱스 (name 등) 는 의도적으로 설정하지 않음.
--       배포 후 쿼리 성능을 먼저 측정하고, 효과가 확인된 시점에 추가할 것.
--       참고 후보: CREATE INDEX idx_speakers_name ON speakers (name);
