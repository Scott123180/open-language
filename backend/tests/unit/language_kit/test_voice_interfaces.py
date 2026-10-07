"""T042: the voice boundary interfaces, and fakes that substitute for them (LSP)."""

from language_kit.voices import VoiceCandidate, VoiceCatalogue, VoiceDownloader
from tests.unit.language_kit.fakes import FakeVoiceCatalogue, FakeVoiceDownloader, candidate


def test_a_candidate_carries_what_the_kit_shows_and_downloads():
    voice = candidate("it_IT-paola-medium")

    assert (voice.key, voice.name, voice.region, voice.country, voice.quality) == (
        "it_IT-paola-medium",
        "paola",
        "it_IT",
        "Italy",
        "medium",
    )
    assert voice.size_bytes == sum(file.size_bytes for file in voice.files)
    assert [file.relative_path.rsplit("/", 1)[1] for file in voice.files] == [
        "it_IT-paola-medium.onnx",
        "it_IT-paola-medium.onnx.json",
    ]
    assert all(file.md5 for file in voice.files)


def test_the_fake_catalogue_is_a_voice_catalogue():
    catalogue = FakeVoiceCatalogue(
        [candidate("it_IT-paola-medium"), candidate("de_DE-thorsten-medium")]
    )

    assert isinstance(catalogue, VoiceCatalogue)
    assert [voice.key for voice in catalogue.candidates("it")] == ["it_IT-paola-medium"]
    assert catalogue.voice("de_DE-thorsten-medium") is not None
    assert catalogue.voice("xx") is None


def test_the_fake_downloader_is_a_voice_downloader(tmp_path):
    downloader = FakeVoiceDownloader(tmp_path)

    download = downloader.ensure(candidate("it_IT-paola-medium"))

    assert isinstance(downloader, VoiceDownloader)
    assert download.downloaded and (tmp_path / "it_IT-paola-medium.onnx").is_file()


def test_a_candidate_is_a_value():
    assert isinstance(candidate("it_IT-paola-medium"), VoiceCandidate)
    assert candidate("it_IT-paola-medium") == candidate("it_IT-paola-medium")
