"""T055: voice files downloaded into the voice directory and checked against their MD5 (R6)."""

import hashlib
from pathlib import Path

import pytest

from language_kit.errors import KitExternalError
from language_kit.voices import (
    VOICE_FILES_URL,
    HttpVoiceDownloader,
    VoiceCandidate,
    VoiceFile,
    download_file,
)

ONNX = b"onnx model bytes"
CONFIG = b'{"audio": {}}'


def _md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()  # noqa: S324 - the catalogue's checksum


def _voice(onnx_md5: str = _md5(ONNX)) -> VoiceCandidate:
    folder = "it/it_IT/paola/medium"
    files = (
        VoiceFile(f"{folder}/it_IT-paola-medium.onnx", onnx_md5, len(ONNX)),
        VoiceFile(f"{folder}/it_IT-paola-medium.onnx.json", _md5(CONFIG), len(CONFIG)),
    )
    return VoiceCandidate(
        "it_IT-paola-medium", "paola", "it_IT", "Italy", "medium", len(ONNX) + len(CONFIG), files
    )


class FakeDownload:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def __call__(self, url: str, destination: Path) -> None:
        self.urls.append(url)
        destination.write_bytes(CONFIG if url.endswith(".json") else ONNX)


class Ticks:
    def __init__(self) -> None:
        self._now = 100.0

    def __call__(self) -> float:
        self._now += 2.0
        return self._now


def _downloader(tmp_path: Path, download=None) -> HttpVoiceDownloader:
    return HttpVoiceDownloader(tmp_path, download or FakeDownload(), timer=Ticks())


def test_both_files_are_downloaded_into_the_voice_directory(tmp_path):
    download = FakeDownload()

    result = _downloader(tmp_path, download).ensure(_voice())

    assert (tmp_path / "it_IT-paola-medium.onnx").read_bytes() == ONNX
    assert (tmp_path / "it_IT-paola-medium.onnx.json").read_bytes() == CONFIG
    assert download.urls == [f"{VOICE_FILES_URL}{file.relative_path}" for file in _voice().files]
    assert (result.key, result.downloaded, result.seconds) == ("it_IT-paola-medium", True, 2.0)


def test_a_file_present_with_the_right_checksum_is_skipped(tmp_path):
    (tmp_path / "it_IT-paola-medium.onnx").write_bytes(ONNX)
    (tmp_path / "it_IT-paola-medium.onnx.json").write_bytes(CONFIG)
    download = FakeDownload()

    result = _downloader(tmp_path, download).ensure(_voice())

    assert download.urls == [] and not result.downloaded


def test_a_file_present_with_the_wrong_checksum_is_downloaded_again(tmp_path):
    (tmp_path / "it_IT-paola-medium.onnx").write_bytes(b"truncated")
    download = FakeDownload()

    _downloader(tmp_path, download).ensure(_voice())

    assert (tmp_path / "it_IT-paola-medium.onnx").read_bytes() == ONNX


def test_a_checksum_mismatch_deletes_the_file_and_fails(tmp_path):
    with pytest.raises(KitExternalError, match="it_IT-paola-medium.onnx"):
        _downloader(tmp_path).ensure(_voice(onnx_md5="0" * 32))

    assert not (tmp_path / "it_IT-paola-medium.onnx").exists()
    assert not list(tmp_path.glob("*.part"))


def test_a_network_error_fails_and_leaves_no_partial_file(tmp_path):
    def broken(url: str, destination: Path) -> None:
        destination.write_bytes(b"half")
        raise OSError("connection reset")

    with pytest.raises(KitExternalError, match="connection reset"):
        _downloader(tmp_path, broken).ensure(_voice())

    assert list(tmp_path.iterdir()) == []


def test_download_file_copies_a_url_to_a_file(tmp_path):
    source = tmp_path / "source.bin"
    source.write_bytes(ONNX)

    download_file(source.as_uri(), tmp_path / "copy.bin")

    assert (tmp_path / "copy.bin").read_bytes() == ONNX
