import ast
from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Tuple

from sampletones_shared.meta.source.bindings.containers import container_item_types
from sampletones_shared.meta.source.constants import module_constants
from sampletones_shared.meta.source.modules import SourceModule


@dataclass(frozen=True)
class SourceIndex:
    """What a tree of modules declares for any one of them to read.

    A module reads names its own source never states — a container annotated elsewhere and walked
    here, a constant declared elsewhere and used here — so reading one module rests on what the
    others declare.
    """

    item_types: Mapping[str, Tuple[str, ...]]
    constants: Mapping[str, ast.expr]


def source_index(modules: Iterable[SourceModule]) -> SourceIndex:
    """Indexes every container annotation and module-level constant of a tree.

    Where two modules declare the same spelling, the module read last states it.

    Args:
        modules: Modules to index.

    Returns:
        SourceIndex: Item types and constant values, each keyed by the spelling naming it.
    """
    item_types: Dict[str, Tuple[str, ...]] = {}
    constants: Dict[str, ast.expr] = {}
    for module in modules:
        item_types.update(container_item_types(module.tree))
        constants.update({constant.name: constant.value for constant in module_constants(module.tree)})

    return SourceIndex(
        item_types=item_types,
        constants=constants,
    )
