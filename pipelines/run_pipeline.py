"""Docker와 CLI에서 전체 데이터 파이프라인을 실행합니다."""

import argparse
import os
import unicodedata
from pathlib import Path
from typing import Callable

from loguru import logger

from pipelines.bill_collection_pipeline import (
    BillInfoLoader,
    BillInfoPipeline,
    BillUrlPipeline,
)
from pipelines.contradiction_candidate_pipeline import build_pipeline
from pipelines.home_snapshot_pipeline import build_pipeline as build_home_pipeline
from pipelines.member_photo_pipeline import MemberPhotoPipeline
from pipelines.pdf_to_speech_pipeline import BillURLToSpeechPipeline, PDFToSpeechPipeline
from pipelines.schedule_to_pdf_pipeline import ScheduleToPDFPipeline
from pipelines.speaker_seed import DEFAULT_CSV_PATH, load_speakers_to_database
from pipelines.utils.db import get_postgres_connection
from pipelines.vectorize_pipeline import VectorizePipeline


DEFAULT_BILL_URL_WORKBOOK_PATH = Path(
    "data/데이터_의안별 회의록 목록.xlsx"
)

DEFAULT_STAGES = (
    "speaker-seed",
    "bill-url-workbook",
    "bill-speech",
    "vectorize",
    "contradiction",
    "home",
)


def _split_stages(value: str | None) -> list[str]:
    """쉼표로 구분된 stage 문자열을 목록으로 변환합니다."""
    if not value:
        return list(DEFAULT_STAGES)
    return [stage.strip() for stage in value.split(",") if stage.strip()]


def _resolve_existing_path(path: Path) -> Path:
    """Unicode 정규화 차이를 고려해 실제 존재하는 파일 경로를 찾습니다.

    Args:
        path: 사용자가 지정했거나 기본값으로 설정된 파일 경로입니다.

    Returns:
        실제 파일 시스템에 존재하는 경로입니다.

    Raises:
        FileNotFoundError: 같은 디렉터리에 정규화 이름이 같은 파일도 없는 경우입니다.
    """
    if path.exists():
        return path

    parent = path.parent
    if not parent.exists():
        raise FileNotFoundError(path)

    expected_names = {
        unicodedata.normalize("NFC", path.name),
        unicodedata.normalize("NFD", path.name),
    }
    for candidate in parent.iterdir():
        candidate_names = {
            unicodedata.normalize("NFC", candidate.name),
            unicodedata.normalize("NFD", candidate.name),
        }
        if expected_names & candidate_names:
            return candidate

    raise FileNotFoundError(path)


def _ensure_bill_info_table() -> None:
    """bill_url 발언 추출 쿼리가 참조하는 bill_info 테이블을 준비합니다."""
    connection = get_postgres_connection()
    try:
        BillInfoLoader(connection).create_table()
    finally:
        connection.close()


def _run_stage(name: str, runner: Callable[[], object]) -> object:
    """단일 파이프라인 stage를 실행하고 로그를 남깁니다."""
    logger.info(f"===== pipeline stage 시작: {name} =====")
    result = runner()
    logger.info(f"===== pipeline stage 완료: {name} / result={result} =====")
    return result


def build_stage_runners(args: argparse.Namespace) -> dict[str, Callable[[], object]]:
    """CLI 인자에 맞는 stage 실행 함수를 구성합니다.

    Args:
        args: `parse_args`가 반환한 CLI 인자입니다.

    Returns:
        stage 이름과 실행 함수 매핑입니다.
    """
    return {
        "speaker-seed": lambda: load_speakers_to_database(
            _resolve_existing_path(args.speaker_csv)
        ),
        "member-photo": lambda: MemberPhotoPipeline(
            assembly_number=args.assembly_number,
            page_size=args.member_photo_page_size,
            max_pages=args.member_photo_max_pages,
            max_workers=args.member_photo_max_workers,
        ).run(),
        "schedule-pdf": lambda: ScheduleToPDFPipeline(
            incremental=True,
            days_back=args.schedule_days_back,
        ).run(),
        "pdf-speech": lambda: PDFToSpeechPipeline().run(),
        "bill-info": lambda: BillInfoPipeline(
            assembly_number=args.assembly_number,
            bill_info_page_size=args.bill_info_page_size,
            bill_info_max_pages=args.bill_info_max_pages,
        ).run(),
        "bill-url": lambda: BillUrlPipeline(
            bill_url_page_size=args.bill_url_page_size,
            bill_url_max_pages=args.bill_url_max_pages,
            bill_url_max_workers=args.bill_url_max_workers,
        ).run(),
        "bill-url-workbook": lambda: (
            _ensure_bill_info_table(),
            BillUrlPipeline(
                bill_url_workbook_path=_resolve_existing_path(args.bill_url_workbook)
            ).run(),
        )[-1],
        "bill-speech": lambda: BillURLToSpeechPipeline().run(),
        "vectorize": lambda: VectorizePipeline(batch_size=args.vectorize_batch_size).run(),
        "contradiction": lambda: build_pipeline(
            recent_limit=args.recent_limit,
            past_limit_per_speaker=args.past_limit_per_speaker,
            similarity_threshold=args.similarity_threshold,
            min_speech_chars=args.min_speech_chars,
            assembly_number=args.assembly_number,
        ).run(),
        "home": lambda: build_home_pipeline().run(),
    }


def parse_args() -> argparse.Namespace:
    """파이프라인 실행 CLI 인자를 파싱합니다."""
    parser = argparse.ArgumentParser(description="Run government project pipelines.")
    parser.add_argument(
        "--stages",
        default=os.getenv("PIPELINE_STAGES"),
        help=(
            "쉼표로 구분된 실행 stage 목록입니다. "
            f"기본값: {','.join(DEFAULT_STAGES)}"
        ),
    )
    parser.add_argument(
        "--speaker-csv",
        type=Path,
        default=Path(os.getenv("SPEAKER_CSV_PATH", DEFAULT_CSV_PATH)),
    )
    parser.add_argument(
        "--bill-url-workbook",
        type=Path,
        default=Path(
            os.getenv("BILL_URL_WORKBOOK_PATH", DEFAULT_BILL_URL_WORKBOOK_PATH)
        ),
    )
    parser.add_argument("--assembly-number", type=int, default=22)
    parser.add_argument("--schedule-days-back", type=int, default=None)
    parser.add_argument("--bill-info-page-size", type=int, default=1000)
    parser.add_argument("--bill-info-max-pages", type=int, default=300)
    parser.add_argument("--bill-url-page-size", type=int, default=10)
    parser.add_argument("--bill-url-max-pages", type=int, default=3)
    parser.add_argument("--bill-url-max-workers", type=int, default=3)
    parser.add_argument("--member-photo-page-size", type=int, default=100)
    parser.add_argument("--member-photo-max-pages", type=int, default=10)
    parser.add_argument("--member-photo-max-workers", type=int, default=1)
    parser.add_argument("--vectorize-batch-size", type=int, default=1000)
    parser.add_argument("--recent-limit", type=int, default=20)
    parser.add_argument("--past-limit-per-speaker", type=int, default=10)
    parser.add_argument("--similarity-threshold", type=float, default=0.6)
    parser.add_argument("--min-speech-chars", type=int, default=50)
    return parser.parse_args()


def main() -> None:
    """선택된 stage를 순서대로 실행합니다."""
    args = parse_args()
    stages = _split_stages(args.stages)
    runners = build_stage_runners(args)
    unknown_stages = [stage for stage in stages if stage not in runners]
    if unknown_stages:
        supported = ", ".join(sorted(runners))
        unknown = ", ".join(unknown_stages)
        raise ValueError(f"지원하지 않는 pipeline stage입니다: {unknown} ({supported})")

    logger.info(f"실행 stage: {', '.join(stages)}")
    for stage in stages:
        _run_stage(stage, runners[stage])


if __name__ == "__main__":
    main()
