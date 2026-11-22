import time
import urllib.request
from pathlib import Path
from typing import Final, List

from sampletones_shared.logger import logger
from sampletones_tools.calibration.config.samples import SampleReference, SamplesConfig
from sampletones_tools.calibration.digest import sha256_digest
from sampletones_tools.runs import output_root

SAMPLES_DIRECTORY: Final[Path] = output_root("calibration") / "samples"
PARTIAL_SUFFIX: Final[str] = ".partial"
TIMEOUT_SECONDS: Final[float] = 60.0


class SampleChecksumError(ValueError):
    """Raised when a downloaded recording differs from the one its reference names."""


def is_fetched(reference: SampleReference, directory: Path) -> bool:
    """Whether the recording stands in ``directory`` and matches its checksum."""
    path = directory / reference.file_name
    return path.is_file() and sha256_digest(path.read_bytes()) == reference.sha256


def fetch_samples(config: SamplesConfig, directory: Path) -> List[Path]:
    """Downloads every referenced recording missing from ``directory``, each checked against its checksum.

    A recording already fetched is kept, so a second run downloads nothing. Downloads introduce
    themselves by the configured name and pause between each other, which keeps a run polite to the
    publishers.

    Args:
        config: The references.
        directory: Where the recordings are kept.

    Returns:
        List[Path]: Every recording the directory holds once the fetch ends.

    Raises:
        SampleChecksumError: If a download differs from the recording its reference names.
        URLError: If a publisher cannot be reached.
    """
    directory.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    for reference in config.samples:
        if is_fetched(reference, directory):
            continue

        if downloaded:
            time.sleep(config.pause_seconds)

        _fetch(reference, config.user_agent, directory)
        downloaded += 1

    return [directory / reference.file_name for reference in config.samples]


def _fetch(reference: SampleReference, user_agent: str, directory: Path) -> None:
    """Downloads one recording and writes it whole once it matches its checksum.

    The download lands under a partial name and takes its own name in one step, so the directory
    holds a recording whole or not at all.

    Raises:
        SampleChecksumError: If the download differs from the recording its reference names.
    """
    logger.info(f"Fetching {reference.name} from {reference.url}")
    data = _download(reference.url, user_agent)
    if sha256_digest(data) != reference.sha256:
        raise SampleChecksumError(
            f"{reference.url} no longer holds the recording {reference.name!r} names; its checksum differs"
        )

    partial = directory / f"{reference.file_name}{PARTIAL_SUFFIX}"
    partial.write_bytes(data)
    partial.replace(directory / reference.file_name)


def _download(url: str, user_agent: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return bytes(response.read())
