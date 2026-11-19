from dataclasses import dataclass
from typing import Callable, Collection, List, Optional, Tuple

from sampletones_core.configs import Config
from sampletones_tools.calibration.config.chords import ChordsConfig
from sampletones_tools.calibration.config.corpus import CorpusConfig
from sampletones_tools.calibration.config.manifest import CorpusManifest
from sampletones_tools.calibration.config.notes import NotesConfig
from sampletones_tools.calibration.config.pitched import PitchedConfig
from sampletones_tools.calibration.config.sequences import SequencesConfig

from .chords import build_chords
from .families import FAMILY_ORDER, Family
from .item import CorpusItem
from .manifest import build_manifest, manifest_catalog
from .nes import build_sequences
from .notes import NOTE_CATEGORIES, build_notes
from .pitched import PITCHED_CATALOG, build_pitched
from .synthesis import PROBE_FAMILIES, build_corpus, corpus_probes

Catalog = List[Tuple[Family, str]]


@dataclass(frozen=True)
class CorpusSource:
    """One source of reference sounds: the categories it holds, and how its sounds are made.

    Attributes:
        catalog: Every category the source holds, beside its family, in the order it holds them.
        build: Makes the source's sounds at a configuration's rates.
    """

    catalog: Catalog
    build: Callable[[Config], List[CorpusItem]]


def reference_corpus(
    config: Config,
    categories: Collection[str],
    manifest: Optional[CorpusManifest],
) -> List[CorpusItem]:
    """The reference sounds of ``categories``, family by family in the order a report presents them.

    A source is made only where it holds a category asked for, so a run of a few categories spends
    nothing on the rest.

    Args:
        config: The configuration the run converts with, whose rates the sounds are made at.
        categories: The categories asked for.
        manifest: The local sounds that join the packaged ones, or ``None`` for the packaged alone.
    """
    items = [
        item
        for source in _sources(manifest)
        if any(category in categories for _, category in source.catalog)
        for item in source.build(config)
        if item.category in categories
    ]
    return sorted(items, key=lambda item: FAMILY_ORDER[item.family])


def reference_catalog(manifest: Optional[CorpusManifest]) -> Catalog:
    """Every category the reference sounds fall in, beside its family, in the order the corpus holds them.

    Args:
        manifest: The local sounds that join the packaged ones, or ``None`` for the packaged alone.
    """
    entries = [entry for source in _sources(manifest) for entry in source.catalog]
    return sorted(dict.fromkeys(entries), key=lambda entry: FAMILY_ORDER[entry[0]])


def reference_categories(manifest: Optional[CorpusManifest]) -> List[str]:
    """The categories of the reference sounds, in the order the corpus first holds each."""
    return [category for _, category in reference_catalog(manifest)]


def _sources(manifest: Optional[CorpusManifest]) -> List[CorpusSource]:
    probes = CorpusConfig.load()
    pitched = PitchedConfig.load()
    sequences = SequencesConfig.load()
    grid = NotesConfig.load()
    chords = ChordsConfig.load()
    return [
        CorpusSource(
            catalog=[(PROBE_FAMILIES[probe.category], probe.category) for probe in corpus_probes(probes)],
            build=lambda config: build_corpus(config.library.sample_rate, config.library.nes_frequency, config=probes),
        ),
        CorpusSource(
            catalog=PITCHED_CATALOG,
            build=lambda config: build_pitched(
                config.library.sample_rate, config.library.nes_frequency, config=pitched
            ),
        ),
        CorpusSource(
            catalog=[(Family.NOTES, category) for category in NOTE_CATEGORIES],
            build=lambda config: build_notes(config, grid=grid),
        ),
        CorpusSource(
            catalog=[(Family.CHORDS, chord.category) for chord in chords.chords],
            build=lambda config: build_chords(config, corpus=chords),
        ),
        CorpusSource(
            catalog=[(Family.SEQUENCES, item.category) for item in sequences.items],
            build=lambda config: build_sequences(config, corpus=sequences),
        ),
        *_manifest_sources(manifest),
    ]


def _manifest_sources(manifest: Optional[CorpusManifest]) -> List[CorpusSource]:
    if manifest is None:
        return []

    return [
        CorpusSource(catalog=manifest_catalog(manifest), build=lambda config: build_manifest(config, manifest=manifest))
    ]
