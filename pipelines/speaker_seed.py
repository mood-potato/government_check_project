import argparse
import csv
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from pipelines.utils.db import get_postgres_connection


PROFILE_IMAGE_SOURCE = "국회의원정보통합API.csv 국회의원사진"
PROFILE_IMAGE_LICENSE = "공공데이터포털 이용허락범위 제한 없음"


@dataclass(frozen=True)
class SpeakerSeedRow:
    mona_code: str
    assembly_number: int
    name: str
    political_party: str
    election_district: str | None
    election_type: str | None
    reelection_count: int | None
    gender: str | None
    birth_date: str | None
    profile_image_url: str | None
    profile_image_source: str | None
    profile_image_license: str | None


DEFAULT_CSV_PATH = Path("data") / "국회의원정보통합API.csv"
DEFAULT_OUTPUT_PATH = Path("supabase") / "seed.sql"
CSV_ENCODINGS = ("utf-8-sig", "cp949")

INSERT_COLUMNS = (
    "mona_code",
    "assembly_number",
    "name",
    "political_party",
    "election_district",
    "election_type",
    "reelection_count",
    "gender",
    "birth_date",
    "profile_image_url",
    "profile_image_source",
    "profile_image_license",
)

UPSERT_SPEAKER_SQL = """
INSERT INTO speakers (
    mona_code,
    assembly_number,
    name,
    political_party,
    election_district,
    election_type,
    reelection_count,
    gender,
    birth_date,
    profile_image_url,
    profile_image_source,
    profile_image_license
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
ON CONFLICT (mona_code, assembly_number) DO UPDATE SET
    name = EXCLUDED.name,
    political_party = EXCLUDED.political_party,
    election_district = EXCLUDED.election_district,
    election_type = EXCLUDED.election_type,
    reelection_count = EXCLUDED.reelection_count,
    gender = EXCLUDED.gender,
    birth_date = EXCLUDED.birth_date,
    profile_image_url = EXCLUDED.profile_image_url,
    profile_image_source = EXCLUDED.profile_image_source,
    profile_image_license = EXCLUDED.profile_image_license,
    profile_image_updated_at = CASE
        WHEN EXCLUDED.profile_image_url IS NULL THEN speakers.profile_image_updated_at
        WHEN speakers.profile_image_url IS DISTINCT FROM EXCLUDED.profile_image_url THEN now()
        ELSE speakers.profile_image_updated_at
    END,
    updated_at = now();
"""


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if cleaned.lower() == "null":
        return None
    return cleaned or None


def _required(row: dict[str, str], column: str) -> str:
    value = _clean(row.get(column))
    if value is None:
        raise ValueError(f"required CSV column is empty: {column}")
    return value


def parse_reelection_count(value: str) -> int | None:
    """재선 횟수 문자열을 정수로 변환합니다.

    Args:
        value: "초선", "재선", "4선"처럼 재선 횟수를 나타내는 문자열입니다.

    Returns:
        변환한 재선 횟수입니다. 값이 비어 있거나 숫자를 찾지 못하면 None입니다.
    """
    cleaned = _clean(value)
    if cleaned is None:
        return None
    if cleaned == "초선":
        return 1
    if cleaned == "재선":
        return 2
    match = re.search(r"\d+", cleaned)
    if match:
        return int(match.group(0))
    return None


def parse_assembly_numbers(value: str) -> list[int]:
    """당선대수 문자열에서 국회 대수 목록을 추출합니다.

    Args:
        value: "제9대, 제10대"처럼 국회 대수를 나타내는 문자열입니다.

    Returns:
        추출한 국회 대수 목록입니다.

    Raises:
        ValueError: 문자열에서 국회 대수를 찾지 못한 경우입니다.
    """
    if _clean(value) == "제헌":
        return [1]

    numbers = [int(match) for match in re.findall(r"\d+", value)]
    if not numbers:
        raise ValueError(f"assembly number not found: {value}")
    return numbers


def _is_integrated_api_row(row: dict[str, str]) -> bool:
    return "국회의원코드" in row


def _optional_iso_date(value: str | None) -> str | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    try:
        date.fromisoformat(cleaned)
    except ValueError:
        return None
    return cleaned


def _profile_image_fields(url: str | None) -> tuple[str | None, str | None, str | None]:
    cleaned_url = _clean(url)
    if cleaned_url is None:
        return None, None, None
    return cleaned_url, PROFILE_IMAGE_SOURCE, PROFILE_IMAGE_LICENSE


def _row_to_speaker(row: dict[str, str], assembly_number: int) -> SpeakerSeedRow:
    election_type = _clean(row.get("선거구구분명"))
    election_district = _clean(row.get("선거구명"))
    if election_type == "비례대표":
        election_district = None

    birth_date = _optional_iso_date(row.get("생일일자"))
    profile_image_url, profile_image_source, profile_image_license = (
        _profile_image_fields(row.get("국회의원사진"))
    )

    return SpeakerSeedRow(
        mona_code=_required(row, "국회의원코드"),
        assembly_number=assembly_number,
        name=_required(row, "국회의원명"),
        political_party=_required(row, "정당명"),
        election_district=election_district,
        election_type=election_type,
        reelection_count=parse_reelection_count(row.get("재선구분명", "")),
        gender=_clean(row.get("성별")),
        birth_date=birth_date,
        profile_image_url=profile_image_url,
        profile_image_source=profile_image_source,
        profile_image_license=profile_image_license,
    )


def row_to_speaker(
    row: dict[str, str], assembly_number: int | None = None
) -> SpeakerSeedRow:
    """CSV row를 의원 seed row로 변환합니다.

    Args:
        row: 국회의원 기본정보 CSV row입니다.
        assembly_number: 통합 API row의 특정 당선대수입니다.

    Returns:
        Supabase seed SQL 생성에 사용할 의원 데이터입니다.
    """
    if _is_integrated_api_row(row):
        if assembly_number is None:
            assembly_number = max(parse_assembly_numbers(_required(row, "당선대수")))
        return _row_to_speaker(row, assembly_number)

    election_type = _clean(row.get("당선구분"))
    election_district = _clean(row.get("선거구"))
    if election_type == "비례대표":
        election_district = None

    birth_date = _clean(row.get("생년월일"))
    if birth_date is not None:
        date.fromisoformat(birth_date)

    return SpeakerSeedRow(
        mona_code=_required(row, "monaCode"),
        assembly_number=int(_required(row, "대수")),
        name=_required(row, "이름"),
        political_party=_required(row, "정당"),
        election_district=election_district,
        election_type=election_type,
        reelection_count=parse_reelection_count(row.get("재선횟수(22대기준)", "")),
        gender=_clean(row.get("성별")),
        birth_date=birth_date,
        profile_image_url=None,
        profile_image_source=None,
        profile_image_license=None,
    )


def _sql_text(value: str | None) -> str:
    if value is None:
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


def _sql_int(value: int | None) -> str:
    return "NULL" if value is None else str(value)


def _sql_date(value: str | None) -> str:
    if value is None:
        return "NULL"
    return f"DATE {_sql_text(value)}"


def _speaker_values(speaker: SpeakerSeedRow) -> str:
    values = (
        _sql_text(speaker.mona_code),
        _sql_int(speaker.assembly_number),
        _sql_text(speaker.name),
        _sql_text(speaker.political_party),
        _sql_text(speaker.election_district),
        _sql_text(speaker.election_type),
        _sql_int(speaker.reelection_count),
        _sql_text(speaker.gender),
        _sql_date(speaker.birth_date),
        _sql_text(speaker.profile_image_url),
        _sql_text(speaker.profile_image_source),
        _sql_text(speaker.profile_image_license),
    )
    return "(" + ", ".join(values) + ")"


def _speaker_params(speaker: SpeakerSeedRow) -> tuple[Any, ...]:
    """의원 row를 DB upsert 파라미터로 변환합니다.

    Args:
        speaker: 저장할 의원 row입니다.

    Returns:
        `speakers` upsert 쿼리에 전달할 파라미터입니다.
    """
    return (
        speaker.mona_code,
        speaker.assembly_number,
        speaker.name,
        speaker.political_party,
        speaker.election_district,
        speaker.election_type,
        speaker.reelection_count,
        speaker.gender,
        speaker.birth_date,
        speaker.profile_image_url,
        speaker.profile_image_source,
        speaker.profile_image_license,
    )


class SpeakerDatabaseLoader:
    """의원 기본정보를 `speakers` 테이블에 저장합니다."""

    def __init__(self, connection: Any) -> None:
        """DB 연결을 저장합니다.

        Args:
            connection: psycopg2 호환 DB 연결 객체입니다.
        """
        self.connection = connection

    def create_table(self) -> None:
        """`speakers` 테이블에 사진 메타 컬럼을 보장합니다."""
        with self.connection.cursor() as cursor:
            self._ensure_profile_image_columns(cursor)

    def _ensure_profile_image_columns(self, cursor: Any) -> None:
        """사진 메타 컬럼이 없는 DB에서도 seed 적재가 가능하게 보장합니다."""
        queries = [
            "ALTER TABLE speakers ADD COLUMN IF NOT EXISTS profile_image_url TEXT;",
            "ALTER TABLE speakers ADD COLUMN IF NOT EXISTS profile_image_source TEXT;",
            "ALTER TABLE speakers ADD COLUMN IF NOT EXISTS profile_image_license TEXT;",
            (
                "ALTER TABLE speakers ADD COLUMN IF NOT EXISTS "
                "profile_image_updated_at TIMESTAMPTZ;"
            ),
        ]
        for query in queries:
            cursor.execute(query)

    def load(self, speakers: Iterable[SpeakerSeedRow]) -> int:
        """의원 row 목록을 `speakers` 테이블에 upsert합니다.

        Args:
            speakers: 저장할 의원 row 목록입니다.

        Returns:
            저장을 시도한 의원 row 수입니다.

        Raises:
            Exception: DB 저장에 실패하면 rollback 후 원 예외를 다시 발생시킵니다.
        """
        rows = list(speakers)
        try:
            with self.connection.cursor() as cursor:
                self._ensure_profile_image_columns(cursor)
                for speaker in rows:
                    cursor.execute(UPSERT_SPEAKER_SQL, _speaker_params(speaker))
            self.connection.commit()
            return len(rows)
        except Exception:
            self.connection.rollback()
            raise


def build_seed_sql(speakers: Iterable[SpeakerSeedRow]) -> str:
    """의원 seed row 목록을 Supabase seed SQL로 변환합니다.

    Args:
        speakers: 의원 seed row 목록입니다.

    Returns:
        `speakers` 테이블 upsert SQL입니다.
    """
    rows = list(speakers)
    if not rows:
        raise ValueError("cannot build speakers seed SQL without rows")

    value_sql = ",\n    ".join(_speaker_values(speaker) for speaker in rows)
    columns = ",\n    ".join(INSERT_COLUMNS)

    return f"""-- Generated from {DEFAULT_CSV_PATH}
-- Re-run with: .venv/bin/python -m pipelines.speaker_seed

INSERT INTO speakers (
    {columns}
) VALUES
    {value_sql}
ON CONFLICT (mona_code, assembly_number) DO UPDATE SET
    name = EXCLUDED.name,
    political_party = EXCLUDED.political_party,
    election_district = EXCLUDED.election_district,
    election_type = EXCLUDED.election_type,
    reelection_count = EXCLUDED.reelection_count,
    gender = EXCLUDED.gender,
    birth_date = EXCLUDED.birth_date,
    updated_at = now();
"""


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    """CSV 파일을 지원 인코딩으로 읽습니다."""
    last_error: UnicodeDecodeError | None = None
    for encoding in CSV_ENCODINGS:
        try:
            with path.open(encoding=encoding, newline="") as csv_file:
                return list(csv.DictReader(csv_file))
        except UnicodeDecodeError as error:
            last_error = error

    if last_error is not None:
        raise last_error
    return []


def load_speakers_from_csv(path: Path) -> list[SpeakerSeedRow]:
    """CSV 파일에서 의원 seed row를 읽습니다."""
    speakers = []
    seen_keys = set()
    for row in _read_csv_rows(path):
        if _is_integrated_api_row(row):
            assembly_numbers_text = _clean(row.get("당선대수"))
            if assembly_numbers_text is None:
                continue
            for assembly_number in parse_assembly_numbers(assembly_numbers_text):
                speaker = row_to_speaker(row, assembly_number)
                key = (speaker.mona_code, speaker.assembly_number)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                speakers.append(speaker)
            continue
        speaker = row_to_speaker(row)
        key = (speaker.mona_code, speaker.assembly_number)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        speakers.append(speaker)
    return speakers


def write_seed_sql(csv_path: Path, output_path: Path) -> int:
    """CSV 파일을 읽어 seed SQL 파일을 씁니다.

    Args:
        csv_path: 국회의원 기본정보 CSV 경로입니다.
        output_path: 생성할 seed SQL 경로입니다.

    Returns:
        SQL로 쓴 의원 row 수입니다.
    """
    speakers = load_speakers_from_csv(csv_path)
    unique_keys = {
        (speaker.mona_code, speaker.assembly_number) for speaker in speakers
    }
    if len(unique_keys) != len(speakers):
        raise ValueError("duplicate (mona_code, assembly_number) keys found in CSV")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_seed_sql(speakers), encoding="utf-8")
    return len(speakers)


def load_speakers_to_database(csv_path: Path = DEFAULT_CSV_PATH) -> int:
    """CSV 파일의 의원 기본정보를 `speakers` 테이블에 저장합니다.

    Args:
        csv_path: 국회의원 기본정보 CSV 경로입니다.

    Returns:
        저장을 시도한 의원 row 수입니다.
    """
    speakers = load_speakers_from_csv(csv_path)
    connection = get_postgres_connection()
    try:
        return SpeakerDatabaseLoader(connection).load(speakers)
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Supabase seed SQL for speakers."
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument(
        "--load-db",
        action="store_true",
        help="Load CSV rows directly into the speakers table.",
    )
    args = parser.parse_args()

    if args.load_db:
        count = load_speakers_to_database(args.csv)
        print(f"Loaded {count} speakers to database")
    else:
        count = write_seed_sql(args.csv, args.output)
        print(f"Wrote {count} speakers to {args.output}")


if __name__ == "__main__":
    main()
