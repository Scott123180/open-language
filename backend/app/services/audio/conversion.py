import subprocess
import tempfile
from pathlib import Path


def convert_webm_to_wav(webm_bytes: bytes) -> Path:
    """Convert WebM/Opus audio bytes to 16kHz mono WAV. Returns path to temp WAV file."""
    if not webm_bytes:
        raise ValueError("Audio data is empty")

    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
        f.write(webm_bytes)
        webm_path = Path(f.name)

    wav_path = webm_path.with_suffix(".wav")

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(webm_path),
                "-acodec",
                "pcm_s16le",
                "-ar",
                "16000",
                "-ac",
                "1",
                str(wav_path),
            ],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg conversion failed: {e.stderr.decode()}") from e
    finally:
        webm_path.unlink(missing_ok=True)

    return wav_path
