from pathlib import Path

from app.services.stt.base import STTError, STTProvider, TranscriptionResult


class WhisperSTTProvider(STTProvider):
    def __init__(self, model_size: str = "base", device: str = "auto"):
        self._model_size = model_size
        self._device = device
        self._model = None  # lazy load

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            compute_type = "float16" if self._device in ("cuda", "auto") else "int8"
            self._model = WhisperModel(
                self._model_size,
                device=self._device if self._device != "auto" else "auto",
                compute_type=compute_type,
            )
        return self._model

    def transcribe(self, audio_path: Path, language_hint: str | None = None) -> TranscriptionResult:
        try:
            model = self._get_model()
            segments, info = model.transcribe(
                str(audio_path),
                language=language_hint,
                beam_size=5,
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            return TranscriptionResult(
                text=text,
                detected_language=info.language,
            )
        except Exception as e:
            raise STTError(str(e)) from e
