import pytest
from unittest.mock import MagicMock, patch


class TestSpeechSummarizer:
    @patch.dict("os.environ", {"OPENAI_API_KEY": ""})
    def test_init_without_api_key(self):
        from modules.llm.summarizer import SpeechSummarizer

        summarizer = SpeechSummarizer()

        assert summarizer.client is None
        assert not summarizer.is_available()

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    @patch("modules.llm.summarizer.OpenAI")
    def test_init_with_api_key(self, mock_openai):
        from modules.llm.summarizer import SpeechSummarizer

        summarizer = SpeechSummarizer()

        assert summarizer.client is not None
        assert summarizer.is_available()
        mock_openai.assert_called_once_with(api_key="test-key")

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    @patch("modules.llm.summarizer.OpenAI")
    def test_summarize_short_text_returns_original(self, mock_openai):
        from modules.llm.summarizer import SpeechSummarizer

        summarizer = SpeechSummarizer(min_length=100)
        short_text = "짧은 텍스트"

        result = summarizer.summarize(short_text)

        assert result == short_text
        # API 호출 없어야 함
        mock_openai.return_value.chat.completions.create.assert_not_called()

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    @patch("modules.llm.summarizer.OpenAI")
    def test_summarize_long_text_calls_api(self, mock_openai):
        from modules.llm.summarizer import SpeechSummarizer

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="요약된 텍스트"))]
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        summarizer = SpeechSummarizer(min_length=10)
        long_text = "이것은 충분히 긴 텍스트입니다. 요약이 필요합니다."

        result = summarizer.summarize(long_text)

        assert result == "요약된 텍스트"
        mock_openai.return_value.chat.completions.create.assert_called_once()

    def test_summarize_without_client_returns_none(self):
        from modules.llm.summarizer import SpeechSummarizer

        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            summarizer = SpeechSummarizer()

        result = summarizer.summarize("텍스트")

        assert result is None

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    @patch("modules.llm.summarizer.OpenAI")
    def test_summarize_batch(self, mock_openai):
        from modules.llm.summarizer import SpeechSummarizer

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="요약"))]
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        summarizer = SpeechSummarizer(min_length=5)
        texts = ["긴 텍스트 1입니다", "긴 텍스트 2입니다", "긴 텍스트 3입니다"]

        results = summarizer.summarize_batch(texts)

        assert len(results) == 3
        assert all(r == "요약" for r in results)

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    @patch("modules.llm.summarizer.OpenAI")
    def test_summarize_handles_api_error(self, mock_openai):
        from modules.llm.summarizer import SpeechSummarizer

        mock_openai.return_value.chat.completions.create.side_effect = Exception(
            "API Error"
        )

        summarizer = SpeechSummarizer(min_length=5)
        result = summarizer.summarize("충분히 긴 텍스트입니다")

        assert result is None

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    @patch("modules.llm.summarizer.OpenAI")
    def test_default_model_is_gpt4o_mini(self, mock_openai):
        from modules.llm.summarizer import SpeechSummarizer

        summarizer = SpeechSummarizer()

        assert summarizer.model == "gpt-4o-mini"

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    @patch("modules.llm.summarizer.OpenAI")
    def test_custom_model(self, mock_openai):
        from modules.llm.summarizer import SpeechSummarizer

        summarizer = SpeechSummarizer(model="gpt-4o")

        assert summarizer.model == "gpt-4o"
