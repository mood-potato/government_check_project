from typing import Dict, List

from pipelines.base.base_transformer import BaseTransformer


class CongressScheduleTransformer(BaseTransformer):
    """
    국회 일정 데이터에서 날짜 리스트를 추출하여 반환하는 클래스
    """

    def transform(self, schedule_data: List[Dict]):
        meeting_dates = sorted(set(item["MEETTING_DATE"] for item in schedule_data))
        return meeting_dates
