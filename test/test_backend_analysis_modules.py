import importlib
import sys


class ElasticsearchImportGuard:
    def __init__(self, *args, **kwargs):
        pass

    def search(self, *args, **kwargs):
        raise AssertionError("Elasticsearch search should not run during import")


class OpenAIImportGuard:
    def __init__(self, *args, **kwargs):
        self.chat = self
        self.completions = self

    def create(self, *args, **kwargs):
        raise AssertionError("OpenAI completion should not run during import")


def test_analysis_modules_do_not_call_external_services_on_import(monkeypatch):
    monkeypatch.setattr("elasticsearch.Elasticsearch", ElasticsearchImportGuard)
    monkeypatch.setattr("openai.OpenAI", OpenAIImportGuard)

    module_names = [
        "backend.modules.analysis.get_all_speark",
        "backend.modules.analysis.get_api_module",
        "backend.modules.analysis.query_speak",
        "backend.modules.analysis.summary_meeting_speak",
    ]

    for module_name in module_names:
        sys.modules.pop(module_name, None)
        importlib.import_module(module_name)
