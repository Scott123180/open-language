# Speech-to-Text Integration Guide

How to embed mic capture + faster-whisper transcription into another Python project,
without the GUI layer.

---

## Core Concept

Two independent services do all the work:

1. **`AudioRecorder`** — opens the default microphone via `sounddevice`, accumulates
   raw frames in memory, and writes a temp WAV on demand.
2. **`TranscriptionEngine`** — wraps `faster-whisper`; auto-selects CUDA (float16,
   then int8_float16), falls back to CPU (int8) transparently.

Neither knows about the other. You wire them together in your application code.

---

## Dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    "faster-whisper>=1.0",   # wraps CTranslate2 + Whisper models
    "sounddevice>=0.4",      # PortAudio bindings for mic capture
    "scipy>=1.11",           # WAV file I/O
    "numpy>=1.24",           # audio frame buffer
]

# Optional: CUDA runtime libs (NVIDIA GPU only, no system CUDA install needed)
[project.optional-dependencies]
cuda = [
    "nvidia-cublas-cu12",
    "nvidia-cuda-runtime-cu12",
    "nvidia-cudnn-cu12",
]
```

Install:
```bash
pip install -e "."           # CPU only
pip install -e ".[cuda]"     # + CUDA runtime libs for GPU
```

**System requirement**: PortAudio must be installed for `sounddevice`.
```bash
# Ubuntu/Debian
sudo apt install libportaudio2
```

---

## CUDA Library Preloading

CTranslate2 loads CUDA `.so` files lazily on the **first inference**, not at import
time. If you installed the `nvidia-*` pip packages, you must load them into the
process *before* importing `faster_whisper` — otherwise `dlopen("libcublas.so.12")`
will fail even if the libraries are present in the venv.

Put this at the very top of your entry point, before any other imports:

```python
import ctypes
import os


def _preload_nvidia_libs() -> None:
    """Preload pip-installed CUDA .so files so ctranslate2 finds them via dlopen."""
    try:
        import nvidia  # namespace package from nvidia-*-cu12 pip packages
    except ImportError:
        return  # no GPU packages installed — CPU path will be used

    # nvidia is a namespace package: __file__ is None, __path__ has the directory
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

# Now safe to import faster-whisper / ctranslate2
from faster_whisper import WhisperModel  # noqa: E402
```

---

## AudioRecorder

```python
# audio/recorder.py
import numpy as np
import scipy.io.wavfile as wav
import sounddevice as sd


SAMPLE_RATE = 16_000   # faster-whisper expects 16 kHz
CHANNELS    = 1        # mono
DTYPE       = "float32"


class AudioData:
    def __init__(self, frames: list, sample_rate: int) -> None:
        self.frames = frames
        self.sample_rate = sample_rate

    def to_wav_file(self, path: str) -> None:
        audio = np.concatenate(self.frames) if self.frames else np.array([], dtype=np.float32)
        wav.write(path, self.sample_rate, audio)


class AudioRecorder:
    def __init__(self) -> None:
        self._frames: list = []
        self._stream = None
        self._recording = False

    def start(self) -> None:
        """Open the default microphone and begin buffering frames."""
        self._frames = []
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE,
            callback=lambda data, *_: self._frames.append(data.copy()),
        )
        self._stream.start()
        self._recording = True

    def stop(self) -> AudioData:
        """Stop recording; return buffered audio."""
        self._stream.stop()
        self._stream.close()
        self._stream = None
        self._recording = False
        return AudioData(list(self._frames), SAMPLE_RATE)

    def discard(self) -> None:
        """Stop recording and throw away the buffer."""
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._frames = []
        self._recording = False
```

---

## TranscriptionEngine

```python
# transcription/engine.py
import tempfile, os
from dataclasses import dataclass
from faster_whisper import WhisperModel

_CUDA_CANDIDATES = [("cuda", "float16"), ("cuda", "int8_float16")]
_CPU_FALLBACK    = ("cpu", "int8")
_CUDA_KEYWORDS   = ("cuda", "cublas", "libcuda", "cufft", "cudnn")

VALID_MODELS = {"tiny", "base", "small", "medium", "large-v3", "distil-large-v3"}


@dataclass
class TranscriptionResult:
    text: str
    model_id: str


class TranscriptionEngine:
    """
    Loads a faster-whisper model; prefers CUDA, falls back to CPU.

    - CUDA init errors (wrong compute type, no CUDA support) → caught at load time.
    - CUDA lazy-load errors (missing libcublas etc.) → caught on first transcribe(),
      engine silently reloads on CPU and retries.
    """

    def __init__(self, model_id: str = "base") -> None:
        if model_id not in VALID_MODELS:
            raise ValueError(f"Unknown model: '{model_id}'")
        self._model_id = model_id
        self._device, self._model = self._load_model(model_id)

    def _load_model(self, model_id: str) -> tuple[str, WhisperModel]:
        for device, compute_type in _CUDA_CANDIDATES:
            try:
                return device, WhisperModel(model_id, device=device, compute_type=compute_type)
            except (RuntimeError, ValueError):
                continue
        # CPU fallback
        return _CPU_FALLBACK[0], WhisperModel(model_id, device=_CPU_FALLBACK[0],
                                               compute_type=_CPU_FALLBACK[1])

    def transcribe(self, audio_path: str) -> TranscriptionResult:
        try:
            segments, _ = self._model.transcribe(audio_path)
            text = " ".join(seg.text for seg in segments).strip()
            return TranscriptionResult(text=text, model_id=self._model_id)
        except Exception as exc:
            # Lazy CUDA failure: reload on CPU and retry once
            if self._device != "cpu" and any(k in str(exc).lower() for k in _CUDA_KEYWORDS):
                self._device, self._model = _CPU_FALLBACK[0], WhisperModel(
                    self._model_id, device=_CPU_FALLBACK[0], compute_type=_CPU_FALLBACK[1]
                )
                segments, _ = self._model.transcribe(audio_path)
                return TranscriptionResult(
                    text=" ".join(seg.text for seg in segments).strip(),
                    model_id=self._model_id,
                )
            raise

    @property
    def device(self) -> str:
        return self._device  # "cuda" or "cpu"
```

---

## Wiring It Together

Recording and transcription must run on **background threads** — both block
indefinitely and would freeze any event loop (GUI, asyncio, etc.).

### Pattern: Thread + Queue

```python
import queue
import tempfile
import threading

recorder = AudioRecorder()
engine   = TranscriptionEngine(model_id="base")
results: queue.Queue = queue.Queue()


def start_recording():
    recorder.start()


def accept_and_transcribe():
    """Call from main thread when user accepts the recording."""
    audio = recorder.stop()

    def _worker():
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            audio.to_wav_file(path)
            result = engine.transcribe(path)
            results.put(("ok", result.text))
        except Exception as exc:
            results.put(("error", str(exc)))
        finally:
            os.unlink(path)

    threading.Thread(target=_worker, daemon=True).start()


def discard_recording():
    recorder.discard()


# Poll results.get(block=False) in your event loop / callback
```

### Pattern: asyncio

```python
import asyncio

async def transcribe_async(audio: AudioData, engine: TranscriptionEngine) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    try:
        audio.to_wav_file(path)
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, engine.transcribe, path)
        return result.text
    finally:
        os.unlink(path)
```

---

## Model Selection

| Model | Size | Speed (CPU) | Accuracy |
|-------|------|-------------|----------|
| `tiny` | 75 MB | Very fast | Low |
| `base` | 145 MB | Fast | OK — good default |
| `small` | 480 MB | Moderate | Good |
| `medium` | 1.5 GB | Slow | Very good |
| `large-v3` | 3 GB | Very slow | Best |
| `distil-large-v3` | 1.5 GB | Fast | Near large-v3 quality |

Models are downloaded from HuggingFace on first use and cached at
`~/.cache/huggingface/hub/`. To pre-download:

```python
from faster_whisper import WhisperModel
WhisperModel("base")  # downloads and caches
```

---

## Key Constraints

- **Audio format**: faster-whisper requires 16 kHz, mono, float32. The recorder
  is already configured for this. If you're bringing your own audio source, resample
  to 16 kHz before passing to `engine.transcribe()`.
- **WAV file handoff**: faster-whisper accepts a file path, not raw bytes. Write
  to a `tempfile.NamedTemporaryFile` and delete it after transcription.
- **Thread safety**: `WhisperModel.transcribe()` is not thread-safe. One call at
  a time — use a queue or lock if multiple callers share one engine instance.
- **Model switching**: Create a new `TranscriptionEngine` with the new `model_id`.
  The old model will be garbage-collected.
