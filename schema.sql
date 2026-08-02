-- 이 파일은 문서가 아니라 실행되는 DDL입니다.
-- `pipelines/utils/schema.py`의 `load_table_ddl()`이 `-- @table: <name>` 구분선 기준으로
-- 섹션을 읽어 각 Loader의 `create_table()`에서 그대로 실행합니다.
-- 모든 문장은 IF NOT EXISTS 기반이라 몇 번을 실행해도 안전합니다.

-- @table: speakers
CREATE TABLE IF NOT EXISTS speakers (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    mona_code         TEXT        NOT NULL,
    assembly_number   INT         NOT NULL,
    name              TEXT        NOT NULL,
    political_party   TEXT        NOT NULL,
    election_district TEXT,                 -- 비례대표는 NULL 허용
    election_type     TEXT,                 -- 지역구 / 비례대표
    reelection_count  INT,                  -- "4선" → 4
    gender            TEXT,
    birth_date        DATE,
    profile_image_url TEXT,
    profile_image_source TEXT,
    profile_image_license TEXT,
    profile_image_updated_at TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_speakers_mona_assembly UNIQUE (mona_code, assembly_number)
);

-- 예전에 만들어진 speakers 테이블에도 사진 메타 컬럼을 보장합니다.
ALTER TABLE speakers ADD COLUMN IF NOT EXISTS profile_image_url TEXT;
ALTER TABLE speakers ADD COLUMN IF NOT EXISTS profile_image_source TEXT;
ALTER TABLE speakers ADD COLUMN IF NOT EXISTS profile_image_license TEXT;
ALTER TABLE speakers ADD COLUMN IF NOT EXISTS profile_image_updated_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_speakers_name ON speakers (name);

-- @table: pdf_url
CREATE TABLE IF NOT EXISTS pdf_url (
    pdf_url_id       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    confer_number    INT,                              -- 회의 회차 번호
    dae_number       INT,                              -- 대수
    date             DATE        NOT NULL,              -- 회의 날짜
    title            TEXT        NOT NULL,              -- 회의 제목
    class_name       TEXT,                              -- 회의 분류명
    sub_name         TEXT,                              -- 부제목 또는 추가 정보
    vod_link         TEXT,                              -- 영상 링크
    conf_link        TEXT,                              -- 회의록 링크
    pdf_url          TEXT,                              -- PDF 파일 주소
    get_pdf          BOOLEAN     DEFAULT FALSE,          -- PDF 추출 여부

    CONSTRAINT unique_pdf UNIQUE (date, title, pdf_url)
);

-- @table: speeches
CREATE TABLE IF NOT EXISTS speeches (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    pdf_url_id      TEXT        NOT NULL,              -- 관련 PDF ID
    speaker_id      UUID        REFERENCES speakers (id) ON DELETE SET NULL,
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
    vectorized      BOOLEAN     DEFAULT FALSE,
    created_at      TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_speech UNIQUE (pdf_url_id, speech_number)
);

-- 예전에 만들어진 speeches 테이블도 최신 컬럼 구성으로 보정합니다.
ALTER TABLE speeches ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE speeches ADD COLUMN IF NOT EXISTS summary TEXT;
ALTER TABLE speeches ADD COLUMN IF NOT EXISTS vectorized BOOLEAN DEFAULT FALSE;
ALTER TABLE speeches ADD COLUMN IF NOT EXISTS speaker_name TEXT;
ALTER TABLE speeches ADD COLUMN IF NOT EXISTS speaker_title TEXT;

UPDATE speeches s
SET speaker_name = sp.name
FROM speakers sp
WHERE s.speaker_id = sp.id
  AND s.speaker_name IS NULL;

ALTER TABLE speeches ALTER COLUMN speaker_id DROP NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'unique_speech'
    ) THEN
        ALTER TABLE speeches
        ADD CONSTRAINT unique_speech UNIQUE (pdf_url_id, speech_number);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_speeches_pdf_url_id ON speeches (pdf_url_id);
CREATE INDEX IF NOT EXISTS idx_speeches_speaker_id ON speeches (speaker_id);
CREATE INDEX IF NOT EXISTS idx_speeches_speaker_name ON speeches (speaker_name);
CREATE INDEX IF NOT EXISTS idx_speeches_vectorized ON speeches (vectorized);
CREATE INDEX IF NOT EXISTS idx_speeches_recent_member
ON speeches (date DESC, speech_number DESC)
WHERE speaker_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_speeches_speaker_date_order
ON speeches (speaker_id, date ASC, speech_number ASC)
WHERE speaker_id IS NOT NULL;

-- @table: home_section_snapshot
CREATE TABLE IF NOT EXISTS home_section_snapshot (
    section_key      text PRIMARY KEY,
    payload          jsonb NOT NULL,
    calculated_at    timestamptz NOT NULL DEFAULT now(),
    expires_at       timestamptz,
    version          integer NOT NULL DEFAULT 1
);

-- @table: bill_info
CREATE TABLE IF NOT EXISTS bill_info (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id      TEXT        NOT NULL,              -- 회의 ID (예: N054183)
    dae_number      INT         NOT NULL,              -- 대수 (예: 22)
    session_number  INT         NOT NULL,              -- 회기 (예: 434)
    confer_number   INT         NOT NULL,              -- 차수 (예: 3)
    bill_id         TEXT        NOT NULL,              -- 의안 ID (PRC_...)
    bill_name       TEXT        NOT NULL,              -- 의안명
    bill_order      INT,                               -- 번호 (예: 14, 15…)
    detail_link     TEXT,                              -- 의안 상세 링크
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_bill_info_meeting_bill ON bill_info (meeting_id, bill_id);
CREATE INDEX IF NOT EXISTS idx_bill_info_bill_id ON bill_info (bill_id);

-- @table: bill_url
CREATE TABLE IF NOT EXISTS bill_url (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    agenda_id       TEXT        NOT NULL,              -- 의안 ID (PRC_...)
    agenda_name     TEXT        NOT NULL,              -- 의안명
    meeting_type    TEXT        NOT NULL,              -- 회의 종류 (예: 국회본회의 회의록)
    meeting_id      TEXT        NOT NULL,              -- 회의 ID (예: N054183)
    dae_number      INT         NOT NULL,              -- 대수 (예: 22)
    meeting_date    DATE        NOT NULL,              -- 회의일자
    download_url    TEXT        NOT NULL,              -- PDF 다운로드 URL
    get_pdf         BOOLEAN     NOT NULL DEFAULT FALSE, -- PDF 수집 여부
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_bill_url_agenda_meeting_download ON bill_url (agenda_id, meeting_id, download_url);
CREATE INDEX IF NOT EXISTS idx_bill_url_get_pdf ON bill_url (get_pdf);
CREATE INDEX IF NOT EXISTS idx_bill_url_agenda_id ON bill_url (agenda_id);

-- @table: contradiction_candidates
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

-- @table: pipeline_monitoring
CREATE TABLE IF NOT EXISTS pipeline_runs (
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

CREATE TABLE IF NOT EXISTS pipeline_row_events (
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
