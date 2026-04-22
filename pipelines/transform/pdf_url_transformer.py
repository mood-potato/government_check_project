from collections import defaultdict
from typing import List, Dict
from pipelines.base.base_transformer import BaseTransformer


class PDFUrlTransformer(BaseTransformer):
    def transform(self, pdf_data_list: List[Dict]):
        grouped = defaultdict(list)

        for item in pdf_data_list:
            key = (item.get("CONF_DATE"), item.get("TITLE"), item.get("CONFER_NUM"))
            grouped[key].append(item)

        transformed_data = []
        for (date, title, confer_num), group_items in grouped.items():
            merged = group_items[0].copy()
            merged["SUB_NAME"] = "\n".join(
                item.get("SUB_NAME", "") for item in group_items
            )
            transformed_data.append(
                {
                    "CONFER_NUM": merged.get("CONFER_NUM"),
                    "DAE_NUM": merged.get("DAE_NUM"),
                    "CONF_DATE": merged.get("CONF_DATE"),
                    "TITLE": merged.get("TITLE"),
                    "CLASS_NAME": merged.get("CLASS_NAME"),
                    "SUB_NAME": merged.get("SUB_NAME"),
                    "VOD_LINK_URL": merged.get("VOD_LINK_URL"),
                    "CONF_LINK_URL": merged.get("CONF_LINK_URL"),
                    "PDF_LINK_URL": merged.get("PDF_LINK_URL"),
                    "get_pdf": False,
                }
            )

        return transformed_data
