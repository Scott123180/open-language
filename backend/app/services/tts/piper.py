from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.services.tts.base import TTSError, TTSProvider, VoiceInstallation

_executor = ThreadPoolExecutor(max_workers=2)
_VOICE_FILE_SUFFIXES = (".onnx", ".onnx.json")


class PiperTTSProvider(TTSProvider):
    def __init__(self, voice_name: str, voice_dir: Path) -> None:
        self._voice_name = voice_name
        self._voice_dir = Path(voice_dir).expanduser()
        self._voice = None  # lazy load

    def _get_voice(self):
        if self._voice is None:
            from piper.voice import PiperVoice

            model_path = self._voice_dir / f"{self._voice_name}.onnx"
            self._voice = PiperVoice.load(str(model_path))
        return self._voice

    @property
    def voice_name(self) -> str:
        return self._voice_name

    def synthesize(self, text: str, output_path: Path) -> None:
        try:
            import wave

            voice = self._get_voice()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with wave.open(str(output_path), "wb") as wav_file:
                voice.synthesize_wav(text, wav_file)
        except Exception as e:
            raise TTSError(str(e)) from e


class PiperVoiceInstallation(VoiceInstallation):
    """A Piper voice is installed when its model and its config are both in the voice folder."""

    def __init__(self, voice_dir: Path) -> None:
        self._voice_dir = Path(voice_dir).expanduser()

    @property
    def voice_dir(self) -> Path:
        return self._voice_dir

    def is_installed(self, voice_key: str) -> bool:
        return all((self._voice_dir / f"{voice_key}{s}").is_file() for s in _VOICE_FILE_SUFFIXES)
