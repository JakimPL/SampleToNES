import argparse
from pathlib import Path
from typing import Final, List, Optional, Tuple

from codec_study.corpus.build import build_corpus
from codec_study.manifest import StudyManifest, StudySource
from codec_study.measure import Measurement, measure
from codec_study.report.run import run_directory, write_run
from codec_study.variants.baselines import Baselines
from codec_study.variants.registry import EVERY_VARIANT, selected_variants
from codec_study.variants.strategy import STRATEGY_ORDER, depth_measurements
from sampletones_shared.logger import logger

DEFAULT_LENGTHEN_SECONDS: Final[int] = 180
DEFAULT_VARIANTS: Final[str] = EVERY_VARIANT


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure the song codec over the projects and stems on this machine.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="A manifest a run wrote; its lengthening and variants stand in for the options below.",
    )
    parser.add_argument(
        "--project",
        type=Path,
        action="append",
        default=[],
        help="A project file to measure, in place of the default corpus; repeatable.",
    )
    parser.add_argument(
        "--reconstruction",
        type=Path,
        action="append",
        default=[],
        help="A stem file, or a directory of stems, in place of the default corpus; repeatable.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory of the run.",
    )
    parser.add_argument(
        "--lengthen",
        type=int,
        default=DEFAULT_LENGTHEN_SECONDS,
        help="Seconds each project's lengthened copy lasts.",
    )
    parser.add_argument(
        "--variants",
        type=str,
        default=DEFAULT_VARIANTS,
        help="Comma-separated variants every song is encoded under, or all; the baseline always runs.",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Read one small project and one stem, to check the harness.",
    )
    arguments = parser.parse_args()

    manifest = _manifest(
        arguments.manifest,
        projects=arguments.project,
        reconstructions=arguments.reconstruction,
        lengthen_seconds=arguments.lengthen,
        variants=_names(arguments.variants),
        quick=arguments.quick,
    )
    variants = selected_variants(manifest.variants, Baselines())
    directory = run_directory(arguments.output)
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


def _names(variants: str) -> Tuple[str, ...]:
    return tuple(name.strip() for name in variants.split(",") if name.strip())


def _manifest(
    path: Optional[Path],
    *,
    projects: List[Path],
    reconstructions: List[Path],
    lengthen_seconds: int,
    variants: Tuple[str, ...],
    quick: bool,
) -> StudyManifest:
    manifest = (
        StudyManifest.load(path)
        if path is not None
        else StudyManifest.default(
            lengthen_seconds=lengthen_seconds,
            variants=variants,
            quick=quick,
        )
    )
    if not projects and not reconstructions:
        return manifest

    return StudyManifest(
        projects=tuple(StudySource.at(project) for project in projects),
        reconstructions=tuple(StudySource.at(reconstruction) for reconstruction in reconstructions),
        lengthen_seconds=manifest.lengthen_seconds,
        variants=manifest.variants,
    )


if __name__ == "__main__":
    main()
