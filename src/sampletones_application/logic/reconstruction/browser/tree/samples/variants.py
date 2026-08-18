from typing import Dict, List, Sequence

from sampletones_application.logic.reconstruction.browser.tree.entries.directory import (
    DirectoryEntry,
)
from sampletones_application.logic.reconstruction.browser.tree.entries.scan import (
    ReconstructionScan,
)
from sampletones_application.logic.reconstruction.browser.tree.samples.source import (
    SampleSource,
)
from sampletones_application.logic.reconstruction.browser.tree.samples.variant import (
    SampleVariant,
)
from sampletones_core.configs.display import unique_display_names
from sampletones_core.reconstructions.converter.paths import ConfigDirectoryFields
from sampletones_core.structures.tree import ConfigNode, NodeType, TreeNode


def collect_variants(scan: ReconstructionScan) -> Dict[SampleSource, List[SampleVariant]]:
    variants_by_source: Dict[SampleSource, List[SampleVariant]] = {}
    for entry in scan.entries:
        match entry:
            case DirectoryEntry(config=ConfigDirectoryFields() as config):
                for reconstruction in scan.collect_reconstructions(entry.entries):
                    relative_path = reconstruction.path.relative_to(entry.path)
                    source = SampleSource(
                        directory_parts=relative_path.parent.parts,
                        name=relative_path.stem,
                    )
                    variants_by_source.setdefault(source, []).append(
                        SampleVariant(config=config, path=reconstruction.path)
                    )

    return variants_by_source


def append_variants(
    audio_node: TreeNode,
    variants: Sequence[SampleVariant],
) -> None:
    labels = unique_display_names([(variant.config.display_name, variant.config.ch) for variant in variants])
    for variant, label in zip(variants, labels):
        ConfigNode(
            label,
            node_type=NodeType.FILE,
            filepath=variant.path,
            config=variant.config,
            parent=audio_node,
        )
