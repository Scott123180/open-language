"""faster-whisper decodes recorded audio through PyAV before transcribing it.

The STT unit tests mock the model, so nothing else exercises that decode step. A PyAV release
that drops an argument faster-whisper passes (PyAV 19 removed `metadata_errors`) breaks every
recording while the rest of the suite stays green; this test catches it.
"""

import wave
from pathlib import Path

from faster_whisper import decode_audio

SAMPLE_RATE = 16_000


def _write_silent_wav(path: Path, seconds: float) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(b"\x00\x00" * int(SAMPLE_RATE * seconds))


def test_decodes_a_recorded_wav_to_16khz_samples(tmp_path: Path) -> None:
    recording = tmp_path / "recording.wav"
    _write_silent_wav(recording, seconds=0.5)

    samples = decode_audio(str(recording), sampling_rate=SAMPLE_RATE)

    assert len(samples) == SAMPLE_RATE // 2
