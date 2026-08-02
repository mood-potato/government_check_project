"""`schema.sql`에서 테이블별 DDL 텍스트를 읽어옵니다."""
from pathlib import Path

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema.sql"
_MARKER = "-- @table: "


def load_table_ddl(table: str) -> str:
    """`schema.sql`의 `-- @table: {table}` 구분선 아래 DDL 텍스트를 반환합니다.

    Args:
        table: `schema.sql`에 있는 `@table` 마커 이름입니다.

    Returns:
        다음 `@table` 마커 전까지의 SQL 텍스트입니다.

    Raises:
        ValueError: 마커를 찾지 못한 경우입니다.
    """
    text = _SCHEMA_PATH.read_text(encoding="utf-8")
    for block in text.split(_MARKER)[1:]:
        name, _, body = block.partition("\n")
        if name.strip() == table:
            return body.strip()
    raise ValueError(f"schema.sql에 '{table}' 섹션이 없습니다.")
