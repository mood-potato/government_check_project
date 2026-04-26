-- ============================================================
-- speakers
-- ============================================================
CREATE TABLE IF NOT EXISTS  speakers (
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

CREATE INDEX idx_speakers_name ON speakers (name);

-- ============================================================
-- pdf_url
-- ============================================================
CREATE TABLE IF NOT EXISTS  pdf_url (
    pdf_url_id       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    confer_number    INT,                              -- 회의 회차 번호
    dae_number       INT,                              -- 대수
    date             DATE        NOT NULL,             -- 회의 날짜
    title            TEXT        NOT NULL,             -- 회의 제목
    class_name       TEXT,                             -- 회의 분류명
    sub_name         TEXT,                             -- 부제목 또는 추가 정보
    vod_link         TEXT,                             -- 영상 링크
    conf_link        TEXT,                             -- 회의록 링크
    pdf_url          TEXT,                             -- PDF 파일 주소
    get_pdf          BOOLEAN     NOT NULL DEFAULT FALSE,  -- PDF 추출 여부
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- speeches
-- ============================================================
CREATE TABLE IF NOT EXISTS  speeches (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    pdf_url_id      TEXT        NOT NULL,              -- 관련 PDF ID
    speaker_id      UUID        REFERENCES speakers (id),
    speaker_name    TEXT        NOT NULL,              -- 국회의원이 아닌 발언자도 원문 이름 보존
    speaker_title   TEXT,                              -- 의원/장관/위원장 등 회의록상 직책
    speech_number   INT         NOT NULL,              -- 발언 순서 번호
    date            DATE        NOT NULL,              -- 회의 날짜
    title           TEXT,
    class_name      TEXT        NOT NULL,              -- 회의 분류명
    confer_number   INT         NOT NULL,              -- 회의 회차 번호
    dae_number      INT         NOT NULL,              -- 대수
    speech          TEXT        NOT NULL,              -- 발언 내용
    summary         TEXT,
    vectorized      BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT unique_speech UNIQUE (pdf_url_id, speech_number)
);

CREATE INDEX idx_speeches_pdf_url_id ON speeches (pdf_url_id);
CREATE INDEX idx_speeches_speaker_id ON speeches (speaker_id);
CREATE INDEX idx_speeches_speaker_name ON speeches (speaker_name);
CREATE INDEX idx_speeches_vectorized ON speeches (vectorized);

-- ============================================================
-- bill_info  (회의별 의안 목록)
-- ============================================================
CREATE TABLE IF NOT EXISTS  bill_info (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id      TEXT        NOT NULL,              -- 회의 ID (예: N054183)
    dae_number      INT         NOT NULL,              -- 대수 (예: 22)
    session_number  INT         NOT NULL,              -- 회기 (예: 434)
    confer_number   INT         NOT NULL,              -- 차수 (예: 3)
    bill_id         TEXT        NOT NULL,              -- 의안 ID (PRC_...)
    bill_name       TEXT        NOT NULL,              -- 의안명
    bill_order      INT,                               -- 번호 (예: 14, 15…)
    detail_link     TEXT,                              -- 의안 상세 링크
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT idx_bill_info_meeting_bill UNIQUE (meeting_id, bill_id)
);

-- ============================================================
-- bill_url  (의안별 PDF 다운로드 정보)
-- ============================================================
CREATE TABLE IF NOT EXISTS  bill_url (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    agenda_id       TEXT        NOT NULL,              -- 의안 ID (PRC_...)
    agenda_name     TEXT        NOT NULL,              -- 의안명
    meeting_type    TEXT        NOT NULL,              -- 회의 종류 (예: 국회본회의 회의록)
    meeting_id      TEXT        NOT NULL,              -- 회의 ID (예: N054183)
    dae_number      INT         NOT NULL,              -- 대수 (예: 22)
    meeting_date    DATE        NOT NULL,              -- 회의일자
    download_url    TEXT        NOT NULL,              -- PDF 다운로드 URL
    get_pdf         BOOLEAN     NOT NULL DEFAULT FALSE, -- PDF 수집 여부
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT idx_bill_url_agenda_meeting_download UNIQUE (agenda_id, meeting_id, download_url)
);

-- ============================================================
-- pipeline_runs / pipeline_row_events (모니터링)
-- ============================================================
CREATE TABLE IF NOT EXISTS  pipeline_runs (
    run_id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_name   TEXT        NOT NULL,
    status          TEXT        NOT NULL DEFAULT 'running',
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    inserted_count  INT         NOT NULL DEFAULT 0,
    updated_count   INT         NOT NULL DEFAULT 0,
    skipped_count   INT         NOT NULL DEFAULT 0,
    failed_count    INT         NOT NULL DEFAULT 0,
    error_message   TEXT,
    meta            JSONB       NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS  pipeline_row_events (
    id              BIGSERIAL   PRIMARY KEY,
    run_id          UUID        NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    target_table    TEXT        NOT NULL,
    record_key      TEXT        NOT NULL,
    action          TEXT        NOT NULL,
    source_date     DATE,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    meta            JSONB       NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at
ON pipeline_runs (started_at DESC);

CREATE INDEX IF NOT EXISTS idx_pipeline_row_events_run_id
ON pipeline_row_events (run_id);

CREATE INDEX IF NOT EXISTS idx_pipeline_row_events_table_date
ON pipeline_row_events (target_table, source_date);
