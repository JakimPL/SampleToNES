from dataclasses import dataclass
from typing import Tuple

from sampletones_tools.codec.study.manifest import StudyManifest
from sampletones_tools.codec.study.variants.baselines import Baselines
from sampletones_tools.codec.study.variants.registry import selected_variants
from sampletones_tools.codec.study.variants.variant import Variant


@dataclass(frozen=True)
class StudyPlan:
    """What one run measures, and the variants its manifest names, so the two stay in step.

    Attributes:
        manifest: What the run reads, which the run saves to repeat it.
        variants: The variants the manifest's names select, the baseline first.
    """

    manifest: StudyManifest
    variants: Tuple[Variant, ...]


def plan_study(manifest: StudyManifest) -> StudyPlan:
    """The run a manifest describes, its variant names selected over production encodings of their own.

    Args:
        manifest: What the run reads.

    Returns:
        StudyPlan: The manifest beside the variants it names.

    Raises:
        ValueError: If a name is registered to no variant.
    """
    return StudyPlan(manifest=manifest, variants=selected_variants(manifest.variants, Baselines()))
