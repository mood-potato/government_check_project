from pipelines.speaker_seed import (
    DEFAULT_CSV_PATH,
    SpeakerDatabaseLoader,
    build_seed_sql,
    load_speakers_from_csv,
    parse_assembly_numbers,
    parse_reelection_count,
    row_to_speaker,
)


def test_parse_reelection_count_extracts_number():
    assert parse_reelection_count("초선") == 1
    assert parse_reelection_count("재선") == 2
    assert parse_reelection_count("4선") == 4
    assert parse_reelection_count("") is None


def test_parse_assembly_numbers_extracts_all_terms():
    assert parse_assembly_numbers("제헌") == [1]
    assert parse_assembly_numbers("제9대, 제10대") == [9, 10]
    assert parse_assembly_numbers("제22대") == [22]


def test_row_to_speaker_maps_csv_columns_and_nulls_proportional_district():
    row = {
        "대수": "22",
        "monaCode": "ABC123",
        "이름": "테스트",
        "정당": "테스트당",
        "선거구": "비례대표",
        "당선구분": "비례대표",
        "재선횟수(22대기준)": "2선",
        "성별": "여",
        "생년월일": "1980-01-02",
    }

    speaker = row_to_speaker(row)

    assert speaker.assembly_number == 22
    assert speaker.mona_code == "ABC123"
    assert speaker.name == "테스트"
    assert speaker.political_party == "테스트당"
    assert speaker.election_district is None
    assert speaker.election_type == "비례대표"
    assert speaker.reelection_count == 2
    assert speaker.gender == "여"
    assert speaker.birth_date == "1980-01-02"


def test_row_to_speaker_maps_integrated_api_columns():
    row = {
        "국회의원코드": "T2T8225E",
        "국회의원명": "강경숙",
        "정당명": "조국혁신당",
        "선거구명": "비례대표",
        "선거구구분명": "비례대표",
        "재선구분명": "초선",
        "성별": "여",
        "생일일자": "1967-05-02",
        "당선대수": "제22대",
        "국회의원사진": "https://www.assembly.go.kr/static/portal/img/openassm/new/profile.jpg",
    }

    speaker = row_to_speaker(row)

    assert speaker.assembly_number == 22
    assert speaker.mona_code == "T2T8225E"
    assert speaker.name == "강경숙"
    assert speaker.political_party == "조국혁신당"
    assert speaker.election_district is None
    assert speaker.election_type == "비례대표"
    assert speaker.reelection_count == 1
    assert speaker.gender == "여"
    assert speaker.birth_date == "1967-05-02"
    assert (
        speaker.profile_image_url
        == "https://www.assembly.go.kr/static/portal/img/openassm/new/profile.jpg"
    )
    assert speaker.profile_image_source == "국회의원정보통합API.csv 국회의원사진"
    assert speaker.profile_image_license == "공공데이터포털 이용허락범위 제한 없음"


def test_row_to_speaker_ignores_invalid_integrated_api_birth_date():
    row = {
        "국회의원코드": "C1J76609",
        "국회의원명": "강기문",
        "정당명": "테스트당",
        "선거구명": "테스트구",
        "선거구구분명": "지역구",
        "재선구분명": "초선",
        "성별": "남",
        "생일일자": "1999-00-00",
        "당선대수": "제10대",
    }

    speaker = row_to_speaker(row)

    assert speaker.birth_date is None


def test_load_speakers_from_csv_expands_integrated_api_rows(tmp_path):
    csv_path = tmp_path / "members.csv"
    csv_path.write_text(
        "\n".join(
            [
                "국회의원코드,국회의원명,정당명,선거구명,선거구구분명,재선구분명,성별,생일일자,당선대수",
                "D2V1479C,갈봉근,유신정우회,,통일주체국민회의,재선,남,1932-04-06,\"제9대, 제10대\"",
            ]
        ),
        encoding="cp949",
    )

    speakers = load_speakers_from_csv(csv_path)

    assert [speaker.assembly_number for speaker in speakers] == [9, 10]
    assert {speaker.mona_code for speaker in speakers} == {"D2V1479C"}


def test_load_speakers_from_csv_skips_integrated_api_rows_without_assembly(tmp_path):
    csv_path = tmp_path / "members.csv"
    csv_path.write_text(
        "\n".join(
            [
                "국회의원코드,국회의원명,정당명,선거구명,선거구구분명,재선구분명,성별,생일일자,당선대수",
                "5OE21654,손세일,민주당,,지역구,null,남,1935-06-25,null",
            ]
        ),
        encoding="cp949",
    )

    assert load_speakers_from_csv(csv_path) == []


def test_build_seed_sql_upserts_speaker_rows():
    speaker = row_to_speaker(
        {
            "대수": "18",
            "monaCode": "OQ1",
            "이름": "오'테스트",
            "정당": "테스트당",
            "선거구": "서울 테스트구",
            "당선구분": "지역구",
            "재선횟수(22대기준)": "1선",
            "성별": "남",
            "생년월일": "1970-03-04",
        }
    )

    sql = build_seed_sql([speaker])

    assert "INSERT INTO speakers" in sql
    assert "ON CONFLICT (mona_code, assembly_number) DO UPDATE SET" in sql
    assert "'오''테스트'" in sql
    assert "DATE '1970-03-04'" in sql
    assert "profile_image_url" in sql
    assert "profile_image_source" in sql
    assert "profile_image_license" in sql


def test_default_csv_path_points_to_integrated_api_file():
    assert DEFAULT_CSV_PATH.exists()
    assert DEFAULT_CSV_PATH.name == "국회의원정보통합API.csv"


def test_load_speakers_from_default_csv_has_unique_speaker_keys():
    speakers = load_speakers_from_csv(DEFAULT_CSV_PATH)

    unique_keys = {
        (speaker.mona_code, speaker.assembly_number) for speaker in speakers
    }

    assert len(speakers) > 0
    assert len(unique_keys) == len(speakers)


class FakeCursor:
    def __init__(self):
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, params=None):
        self.queries.append((query, params))


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()
        self.commit_count = 0
        self.rollback_count = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        self.rollback_count += 1


def test_database_loader_upserts_speakers():
    speaker = row_to_speaker(
        {
            "대수": "22",
            "monaCode": "ABC123",
            "이름": "테스트",
            "정당": "테스트당",
            "선거구": "서울 테스트구",
            "당선구분": "지역구",
            "재선횟수(22대기준)": "초선",
            "성별": "여",
            "생년월일": "1980-01-02",
        }
    )
    connection = FakeConnection()
    loader = SpeakerDatabaseLoader(connection)

    count = loader.load([speaker])

    assert count == 1
    assert connection.commit_count == 1
    assert connection.rollback_count == 0
    query, params = connection.cursor_instance.queries[-1]
    assert "INSERT INTO speakers" in query
    assert "ON CONFLICT (mona_code, assembly_number) DO UPDATE SET" in query
    assert params == (
        "ABC123",
        22,
        "테스트",
        "테스트당",
        "서울 테스트구",
        "지역구",
        1,
        "여",
        "1980-01-02",
        None,
        None,
        None,
    )


def test_database_loader_ensures_profile_image_columns_before_upsert():
    speaker = row_to_speaker(
        {
            "국회의원코드": "T2T8225E",
            "국회의원명": "강경숙",
            "정당명": "조국혁신당",
            "선거구명": "비례대표",
            "선거구구분명": "비례대표",
            "재선구분명": "초선",
            "성별": "여",
            "생일일자": "1967-05-02",
            "당선대수": "제22대",
            "국회의원사진": "https://www.assembly.go.kr/static/portal/img/openassm/new/profile.jpg",
        }
    )
    connection = FakeConnection()
    loader = SpeakerDatabaseLoader(connection)

    loader.load([speaker])

    schema_query, _ = connection.cursor_instance.queries[0]
    assert "ALTER TABLE speakers ADD COLUMN IF NOT EXISTS profile_image_url TEXT;" in schema_query
    assert (
        "ALTER TABLE speakers ADD COLUMN IF NOT EXISTS profile_image_source TEXT;"
        in schema_query
    )
    assert (
        "ALTER TABLE speakers ADD COLUMN IF NOT EXISTS profile_image_license TEXT;"
        in schema_query
    )
    assert (
        "ALTER TABLE speakers ADD COLUMN IF NOT EXISTS profile_image_updated_at TIMESTAMPTZ;"
        in schema_query
    )
    assert "INSERT INTO speakers" in connection.cursor_instance.queries[-1][0]
