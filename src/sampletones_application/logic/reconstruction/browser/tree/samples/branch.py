from sampletones_application.logic.reconstruction.browser.tree.containers import (
    find_or_create_group,
    find_or_create_sample,
)
from sampletones_application.logic.reconstruction.browser.tree.entries.scan import (
    ReconstructionScan,
)
from sampletones_application.logic.reconstruction.browser.tree.samples.variants import (
    append_variants,
    collect_variants,
)
from sampletones_core.structures.tree import NodeType, TreeNode


def build_sample_branch(
    scan: ReconstructionScan,
    *,
    name: str,
    parent: TreeNode,
) -> TreeNode:
    """Builds the branch listing each source audio with the configurations that reconstructed it.

    Every top-level configuration directory contributes its reconstructions under the source folders
    they mirror, so one audio gathers its variants and each variant is labelled by its configuration.
    """
    branch = TreeNode(name, node_type=NodeType.GROUP, parent=parent)
    variants_by_source = collect_variants(scan)
    for source in sorted(variants_by_source):
        source_node = branch
        for part in source.directory_parts:
            source_node = find_or_create_group(part, parent=source_node)

        audio_node = find_or_create_sample(source.name, parent=source_node)
        append_variants(audio_node, variants_by_source[source])

    return branch
