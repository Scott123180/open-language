import ctypes
import os
from pathlib import Path

from app.services.stt.base import STTError, STTProvider, TranscriptionResult

_CUDA_KEYWORDS = ("cuda", "cublas", "libcuda", "cufft", "cudnn")


def _preload_nvidia_libs() -> None:
    """Preload pip-installed CUDA .so files so ctranslate2 finds them via dlopen."""
    try:
        import nvidia  # namespace package from nvidia-*-cu12 pip packages
    except ImportError:
        return

    nvidia_root = next(iter(nvidia.__path__), None)
    if not nvidia_root:
        return

    for pkg in os.listdir(nvidia_root):
        lib_dir = os.path.join(nvidia_root, pkg, "lib")
        if not os.path.isdir(lib_dir):
            continue
        for fname in os.listdir(lib_dir):
            if fname.endswith(".so") or ".so." in fname:
                try:
                    ctypes.cdll.LoadLibrary(os.path.join(lib_dir, fname))
                except OSError:
                    pass


_preload_nvidia_libs()


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

    def _reload_cpu(self):
        from faster_whisper import WhisperModel

        self._device = "cpu"
        self._model = WhisperModel(self._model_size, device="cpu", compute_type="int8")
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
            if self._device != "cpu" and any(k in str(e).lower() for k in _CUDA_KEYWORDS):
                model = self._reload_cpu()
                try:
                    segments, info = model.transcribe(
                        str(audio_path),
                        language=language_hint,
                        beam_size=5,
                    )
                    text = " ".join(seg.text.strip() for seg in segments).strip()
                    return TranscriptionResult(text=text, detected_language=info.language)
                except Exception as cpu_e:
                    raise STTError(str(cpu_e)) from cpu_e
            raise STTError(str(e)) from e
