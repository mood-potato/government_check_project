import argparse
import csv
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable


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


DEFAULT_CSV_PATH = Path("data") / "18대-22대 국회의원 기본정보 - 정보.csv"
DEFAULT_OUTPUT_PATH = Path("supabase") / "seed.sql"

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
)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
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


def row_to_speaker(row: dict[str, str]) -> SpeakerSeedRow:
    """CSV row를 의원 seed row로 변환합니다.

    Args:
        row: 국회의원 기본정보 CSV row입니다.

    Returns:
        Supabase seed SQL 생성에 사용할 의원 데이터입니다.
    """
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
    )
    return "(" + ", ".join(values) + ")"


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


def load_speakers_from_csv(path: Path) -> list[SpeakerSeedRow]:
    """CSV 파일에서 의원 seed row를 읽습니다."""
    with path.open(encoding="utf-8-sig", newline="") as csv_file:
        return [row_to_speaker(row) for row in csv.DictReader(csv_file)]


def write_seed_sql(csv_path: Path, output_path: Path) -> int:
    """CSV 파일을 읽어 seed SQL 파일을 씁니다.

    Args:
        csv_path: 국회의원 기본정보 CSV 경로입니다.
        output_path: 생성할 seed SQL 경로입니다.

    Returns:
        SQL로 쓴 의원 row 수입니다.
    """
    speakers = load_speakers_from_csv(csv_path)
    unique_keys = {(speaker.mona_code, speaker.assembly_number) for speaker in speakers}
    if len(unique_keys) != len(speakers):
        raise ValueError("duplicate (mona_code, assembly_number) keys found in CSV")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_seed_sql(speakers), encoding="utf-8")
    return len(speakers)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Supabase seed SQL for speakers."
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()

    count = write_seed_sql(args.csv, args.output)
    print(f"Wrote {count} speakers to {args.output}")


if __name__ == "__main__":
    main()
