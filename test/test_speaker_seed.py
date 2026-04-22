from pipelines.speaker_seed import (
    build_seed_sql,
    parse_reelection_count,
    row_to_speaker,
)


def test_parse_reelection_count_extracts_number():
    assert parse_reelection_count("초선") == 1
    assert parse_reelection_count("재선") == 2
    assert parse_reelection_count("4선") == 4
    assert parse_reelection_count("") is None


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
