"""Unit tests for convert_webm_to_wav()."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.audio.conversion import convert_webm_to_wav


def test_raises_value_error_on_empty_bytes():
    with pytest.raises(ValueError, match="empty"):
        convert_webm_to_wav(b"")


def test_subprocess_called_with_correct_ffmpeg_args(tmp_path: Path):
    fake_wav = None

    def fake_run(args, **kwargs):
        nonlocal fake_wav
        # Create the output WAV file that the function expects to return
        wav_arg = args[-1]
        fake_wav = Path(wav_arg)
        fake_wav.write_bytes(b"RIFF....WAVE")
        return MagicMock(returncode=0)

    with patch("app.services.audio.conversion.subprocess.run", side_effect=fake_run) as mock_run:
        result = convert_webm_to_wav(b"\x00\x01\x02\x03")  # noqa: F841

    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]  # positional first arg (the list)

    assert "ffmpeg" in call_args
    assert "-ar" in call_args
    assert "16000" in call_args
    assert "-ac" in call_args
    assert "1" in call_args


def test_returns_path_to_wav_file(tmp_path: Path):
    def fake_run(args, **kwargs):
        wav_arg = args[-1]
        Path(wav_arg).write_bytes(b"RIFF....WAVE")
        return MagicMock(returncode=0)

    with patch("app.services.audio.conversion.subprocess.run", side_effect=fake_run):
        result = convert_webm_to_wav(b"\x00\x01\x02\x03")

    assert isinstance(result, Path)
    assert result.suffix == ".wav"
    assert result.exists()
    # Clean up
    result.unlink(missing_ok=True)


def test_webm_temp_file_deleted_after_conversion(tmp_path: Path):
    created_webm: list[Path] = []

    def fake_run(args, **kwargs):
        # Record webm input path (second arg after -i flag)
        i_idx = args.index("-i")
        webm_path = Path(args[i_idx + 1])
        created_webm.append(webm_path)
        wav_arg = args[-1]
        Path(wav_arg).write_bytes(b"RIFF....WAVE")
        return MagicMock(returncode=0)

    with patch("app.services.audio.conversion.subprocess.run", side_effect=fake_run):
        result = convert_webm_to_wav(b"\x00\x01\x02\x03")

    assert len(created_webm) == 1
    # The webm temp file should have been deleted
    assert not created_webm[0].exists()

    # Clean up result
    result.unlink(missing_ok=True)


def test_raises_runtime_error_on_ffmpeg_failure():
    def fake_run(args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=args,
            stderr=b"FFmpeg error: invalid input",
        )

    with (
        patch("app.services.audio.conversion.subprocess.run", side_effect=fake_run),
        pytest.raises(RuntimeError, match="FFmpeg conversion failed"),
    ):
        convert_webm_to_wav(b"\x00\x01\x02\x03")


def test_acodec_pcm_s16le_in_args():
    def fake_run(args, **kwargs):
        wav_arg = args[-1]
        Path(wav_arg).write_bytes(b"RIFF....WAVE")
        return MagicMock(returncode=0)

    with patch("app.services.audio.conversion.subprocess.run", side_effect=fake_run) as mock_run:
        result = convert_webm_to_wav(b"\x00\x01\x02\x03")

    call_args = mock_run.call_args[0][0]
    assert "-acodec" in call_args
    assert "pcm_s16le" in call_args

    result.unlink(missing_ok=True)
