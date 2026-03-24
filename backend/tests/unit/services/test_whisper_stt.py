"""Unit tests for WhisperSTTProvider."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.stt.base import STTError, TranscriptionResult
from app.services.stt.whisper import WhisperSTTProvider


def _make_segment(text: str) -> MagicMock:
    seg = MagicMock()
    seg.text = text
    return seg


def _make_info(language: str = "es") -> MagicMock:
    info = MagicMock()
    info.language = language
    return info


def _make_mock_model(segments: list[str], language: str = "es") -> MagicMock:
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (
        [_make_segment(t) for t in segments],
        _make_info(language),
    )
    return mock_model


class TestWhisperSTTProviderLazyLoad:
    def test_model_is_none_initially(self):
        provider = WhisperSTTProvider(model_size="base", device="cpu")
        assert provider._model is None

    def test_model_loaded_on_first_transcribe(self):
        provider = WhisperSTTProvider(model_size="base", device="cpu")
        mock_model = _make_mock_model(["Hola"])

        with patch("faster_whisper.WhisperModel", return_value=mock_model) as mock_cls:
            provider.transcribe(Path("/fake/audio.wav"))

        assert provider._model is mock_model
        mock_cls.assert_called_once()

    def test_model_not_reloaded_on_second_transcribe(self):
        provider = WhisperSTTProvider(model_size="base", device="cpu")
        mock_model = _make_mock_model(["Hola"])

        with patch("faster_whisper.WhisperModel", return_value=mock_model) as mock_cls:
            provider.transcribe(Path("/fake/audio.wav"))
            provider.transcribe(Path("/fake/audio.wav"))

        mock_cls.assert_called_once()


class TestWhisperSTTProviderTranscribe:
    def _provider_with_mock_model(self, segments: list[str], language: str = "es") -> tuple:
        provider = WhisperSTTProvider(model_size="base", device="cpu")
        mock_model = _make_mock_model(segments, language)
        provider._model = mock_model
        return provider, mock_model

    def test_transcribe_joins_segments_with_space(self):
        provider, _ = self._provider_with_mock_model(["Buenos", "días", "amigo"])
        result = provider.transcribe(Path("/fake/audio.wav"))
        assert result.text == "Buenos días amigo"

    def test_transcribe_strips_segment_whitespace(self):
        provider, _ = self._provider_with_mock_model(["  Hola  ", " mundo "])
        result = provider.transcribe(Path("/fake/audio.wav"))
        assert result.text == "Hola mundo"

    def test_transcribe_single_segment(self):
        provider, _ = self._provider_with_mock_model(["Hola mundo"])
        result = provider.transcribe(Path("/fake/audio.wav"))
        assert result.text == "Hola mundo"

    def test_transcribe_returns_detected_language(self):
        provider, _ = self._provider_with_mock_model(["Hola"], language="es")
        result = provider.transcribe(Path("/fake/audio.wav"))
        assert result.detected_language == "es"

    def test_transcribe_returns_transcription_result(self):
        provider, _ = self._provider_with_mock_model(["Hola"])
        result = provider.transcribe(Path("/fake/audio.wav"))
        assert isinstance(result, TranscriptionResult)

    def test_language_hint_forwarded_to_model(self):
        provider, mock_model = self._provider_with_mock_model(["Hola"])
        provider.transcribe(Path("/fake/audio.wav"), language_hint="es")
        mock_model.transcribe.assert_called_once_with(
            str(Path("/fake/audio.wav")),
            language="es",
            task="transcribe",
            beam_size=5,
        )

    def test_language_hint_none_forwarded_to_model(self):
        provider, mock_model = self._provider_with_mock_model(["Hola"])
        provider.transcribe(Path("/fake/audio.wav"), language_hint=None)
        mock_model.transcribe.assert_called_once_with(
            str(Path("/fake/audio.wav")),
            language=None,
            task="transcribe",
            beam_size=5,
        )

    def test_stt_error_raised_on_model_exception(self):
        provider = WhisperSTTProvider(model_size="base", device="cpu")
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = RuntimeError("CUDA out of memory")
        provider._model = mock_model

        with pytest.raises(STTError, match="CUDA out of memory"):
            provider.transcribe(Path("/fake/audio.wav"))

    def test_empty_segments_returns_empty_text(self):
        provider, _ = self._provider_with_mock_model([])
        result = provider.transcribe(Path("/fake/audio.wav"))
        assert result.text == ""


class TestWhisperSTTProviderComputeType:
    def test_float16_used_for_cuda_device(self):
        provider = WhisperSTTProvider(model_size="base", device="cuda")
        mock_model = _make_mock_model(["hi"])

        with patch("faster_whisper.WhisperModel", return_value=mock_model) as mock_cls:
            provider.transcribe(Path("/fake/audio.wav"))

        _, kwargs = mock_cls.call_args
        assert kwargs.get("compute_type") == "float16"

    def test_float16_used_for_auto_device(self):
        provider = WhisperSTTProvider(model_size="base", device="auto")
        mock_model = _make_mock_model(["hi"])

        with patch("faster_whisper.WhisperModel", return_value=mock_model) as mock_cls:
            provider.transcribe(Path("/fake/audio.wav"))

        _, kwargs = mock_cls.call_args
        assert kwargs.get("compute_type") == "float16"

    def test_int8_used_for_cpu_device(self):
        provider = WhisperSTTProvider(model_size="base", device="cpu")
        mock_model = _make_mock_model(["hi"])

        with patch("faster_whisper.WhisperModel", return_value=mock_model) as mock_cls:
            provider.transcribe(Path("/fake/audio.wav"))

        _, kwargs = mock_cls.call_args
        assert kwargs.get("compute_type") == "int8"
