from pathlib import Path
from typing import Final, List, Optional, Tuple

from sampletones_shared.logger import logger
from sampletones_tools.codec.study.corpus.build import build_corpus
from sampletones_tools.codec.study.manifest import NO_SOURCE, StudyManifest, StudySource
from sampletones_tools.codec.study.measure import Measurement, measure
from sampletones_tools.codec.study.report.run import run_directory, write_run
from sampletones_tools.codec.study.variants.baselines import Baselines
from sampletones_tools.codec.study.variants.registry import EVERY_VARIANT, selected_variants
from sampletones_tools.codec.study.variants.strategy import STRATEGY_ORDER, depth_measurements

LIST_SEPARATOR: Final[str] = ","


def variant_names(stated: Optional[str]) -> Tuple[str, ...]:
    """The variants a run encodes under: the ones named, comma separated, or every one."""
    if stated is None:
        return (EVERY_VARIANT,)

    return tuple(name.strip() for name in stated.split(LIST_SEPARATOR) if name.strip())


def resolve_manifest(
    path: Optional[Path],
    *,
    projects: Tuple[Path, ...],
    reconstructions: Tuple[Path, ...],
    lengthen_seconds: int,
    variants: Tuple[str, ...],
) -> StudyManifest:
    """The manifest a run measures: the sources named outright, or the ones a manifest file states.

    Sources named outright stand in for a manifest's own, while its lengthening and variants stay.

    Args:
        path: A manifest a run wrote, or ``None`` to measure the sources named outright.
        projects: Project files to measure.
        reconstructions: Stem files, or directories of stems, to measure.
        lengthen_seconds: How long each project's lengthened copy lasts, unless a manifest states it.
        variants: The names of the variants every song is encoded under, unless a manifest states them.

    Raises:
        ValueError: If neither a manifest nor a source is named.
    """
    if path is None and not projects and not reconstructions:
        raise ValueError(NO_SOURCE)

    manifest = StudyManifest.load(path) if path is not None else None
    if manifest is not None and not projects and not reconstructions:
        return manifest

    return StudyManifest(
        projects=tuple(StudySource.at(project) for project in projects),
        reconstructions=tuple(StudySource.at(reconstruction) for reconstruction in reconstructions),
        lengthen_seconds=manifest.lengthen_seconds if manifest is not None else lengthen_seconds,
        variants=manifest.variants if manifest is not None else variants,
    )


def run_study(manifest: StudyManifest, output: Optional[Path]) -> Path:
    """Encodes every song of the manifest under every variant and writes the run.

    Args:
        manifest: What is measured and under which variants.
        output: The directory the run writes into, or ``None`` for a stamped one under the
            documents.

    Returns:
        Path: The directory holding the report, the accounting and the verdicts.

    Raises:
        ValueError: If a variant writes a song as streams that play back differently.
    """
    variants = selected_variants(manifest.variants, Baselines())
    directory = run_directory(output)
    corpus = build_corpus(manifest)

    measurements: List[Measurement] = []
    for song in corpus:
        for variant in variants:
            if not variant.applies(song):
                continue

            logger.info(f"Encoding {song.name} ({song.ticks} ticks) under {variant.name}")
            measurement = measure(song, variant.name, variant.encode)
            if not measurement.lossless:
                raise ValueError(f"{variant.name} wrote {song.name} as streams that play back differently")

            logger.info(
                f"  {measurement.block} bytes, {measurement.bytes_per_tick:.3f} bytes per tick, "
                f"{measurement.phrases} phrases, {measurement.seconds:.1f} s"
            )
            measurements.append(measurement)

    write_run(
        directory,
        manifest,
        variants,
        measurements,
        depth_measurements(measurements, STRATEGY_ORDER),
    )
    logger.info(f"Report written to {directory}")
    return directory
