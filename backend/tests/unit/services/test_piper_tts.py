from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.tts.base import TTSError
from app.services.tts.piper import PiperTTSProvider


def test_voice_name_property(tmp_path: Path) -> None:
    provider = PiperTTSProvider(voice_name="es_ES-mls-medium", voice_dir=tmp_path)
    assert provider.voice_name == "es_ES-mls-medium"


def test_synthesize_calls_voice_synthesize(tmp_path: Path) -> None:
    mock_voice = MagicMock()
    mock_piper_voice_cls = MagicMock(return_value=mock_voice)

    output_path = tmp_path / "output.wav"

    with patch.dict("sys.modules", {"piper": MagicMock(), "piper.voice": MagicMock()}):
        import piper.voice as pv

        pv.PiperVoice = mock_piper_voice_cls

        provider = PiperTTSProvider(voice_name="es_ES-mls-medium", voice_dir=tmp_path)
        provider._voice = mock_voice  # inject already-loaded voice to skip load()

        with patch("wave.open") as mock_wave_open:
            mock_wav_file = MagicMock()
            mock_wave_open.return_value.__enter__ = MagicMock(return_value=mock_wav_file)
            mock_wave_open.return_value.__exit__ = MagicMock(return_value=False)
            provider.synthesize("Hola mundo", output_path)

        mock_voice.synthesize_wav.assert_called_once()
        args = mock_voice.synthesize_wav.call_args[0]
        assert args[0] == "Hola mundo"


def test_synthesize_creates_parent_directories(tmp_path: Path) -> None:
    nested_output = tmp_path / "subdir" / "nested" / "output.wav"
    mock_voice = MagicMock()

    provider = PiperTTSProvider(voice_name="es_ES-mls-medium", voice_dir=tmp_path)
    provider._voice = mock_voice

    with patch("wave.open") as mock_wave_open:
        mock_wave_open.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_wave_open.return_value.__exit__ = MagicMock(return_value=False)
        provider.synthesize("Test", nested_output)

    assert nested_output.parent.exists()


def test_synthesize_raises_tts_error_on_exception(tmp_path: Path) -> None:
    mock_voice = MagicMock()
    mock_voice.synthesize_wav.side_effect = RuntimeError("piper failed")

    provider = PiperTTSProvider(voice_name="es_ES-mls-medium", voice_dir=tmp_path)
    provider._voice = mock_voice

    output_path = tmp_path / "output.wav"

    with patch("wave.open") as mock_wave_open:
        mock_wav_file = MagicMock()
        mock_wave_open.return_value.__enter__ = MagicMock(return_value=mock_wav_file)
        mock_wave_open.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(TTSError, match="piper failed"):
            provider.synthesize("Test text", output_path)


def test_lazy_load_voice(tmp_path: Path) -> None:
    """Voice should be None initially and loaded on first synthesize call."""
    provider = PiperTTSProvider(voice_name="es_ES-mls-medium", voice_dir=tmp_path)
    assert provider._voice is None


def test_get_voice_loads_from_correct_path(tmp_path: Path) -> None:
    """_get_voice loads the .onnx model from voice_dir/voice_name.onnx."""
    mock_voice = MagicMock()
    mock_piper_voice_cls = MagicMock()
    mock_piper_voice_cls.load.return_value = mock_voice

    mock_piper_module = MagicMock()
    mock_piper_module.PiperVoice = mock_piper_voice_cls

    provider = PiperTTSProvider(voice_name="my-voice", voice_dir=tmp_path)
    expected_model_path = str(tmp_path / "my-voice.onnx")

    with patch.dict("sys.modules", {"piper": MagicMock(), "piper.voice": mock_piper_module}):
        result = provider._get_voice()

    mock_piper_voice_cls.load.assert_called_once_with(expected_model_path)
    assert result is mock_voice
