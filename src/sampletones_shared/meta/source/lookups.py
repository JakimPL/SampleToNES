import ast
from dataclasses import dataclass
from itertools import product
from typing import Iterable, List, Sequence, Tuple

from sampletones_shared.meta.source.bindings.scopes import module_scopes
from sampletones_shared.meta.source.index import SourceIndex
from sampletones_shared.meta.source.modules import SourceModule
from sampletones_shared.meta.source.subscripts import SubscriptSite, find_subscripts
from sampletones_shared.meta.source.values import EnumTable, ResolvedValues, ValueResolver


@dataclass(frozen=True)
class LookupSite:
    """One lookup written on a receiver of a known type, and the strings it asks for.

    A lookup whose every part is a literal is exact: it asks for precisely these strings. A lookup
    reaching an enum asks for one string per member combination. A lookup holding a part out of
    reach names that part instead, which is what a caller reports back to its author.
    """

    location: str
    values: Tuple[str, ...]
    exact: bool
    unresolved_parts: Tuple[str, ...]

    @property
    def resolved(self) -> bool:
        return not self.unresolved_parts


def composed_values(resolutions: Sequence[ResolvedValues], separator: str) -> Tuple[str, ...]:
    """Every string a lookup's resolved parts spell together.

    A lookup of one part spells that part's values. A lookup of several parts spells one string per
    combination of them, joined by the separator.

    Args:
        resolutions: Values each part of the lookup resolves to.
        separator: String standing between the parts.

    Returns:
        Tuple[str, ...]: The strings, empty where a part states no values.
    """
    if not all(resolution.resolved for resolution in resolutions):
        return ()

    combinations = product(*(resolution.values for resolution in resolutions))
    return tuple(separator.join(combination) for combination in combinations)


def lookup_site(
    module: SourceModule,
    site: SubscriptSite,
    resolver: ValueResolver,
    separator: str,
) -> LookupSite:
    """Resolves one subscript into the strings it asks for.

    Args:
        module: Module the subscript lives in.
        site: Subscript to read.
        resolver: Resolver holding what the subscript's scope states about its names.
        separator: String standing between the parts of a composed value.

    Returns:
        LookupSite: The lookup, located as `path:line`.
    """
    resolutions = tuple(resolver.resolve(part) for part in site.parts)
    unresolved = (part for part, resolution in zip(site.parts, resolutions, strict=True) if not resolution.resolved)
    return LookupSite(
        location=module.location(site.node),
        values=composed_values(resolutions, separator),
        exact=all(resolution.exact for resolution in resolutions),
        unresolved_parts=tuple(repr(ast.unparse(part)) for part in unresolved),
    )


def module_lookups(
    module: SourceModule,
    *,
    index: SourceIndex,
    enums: EnumTable,
    receiver_type: str,
    separator: str,
) -> List[LookupSite]:
    """Every lookup one module writes on a receiver of the named type.

    Args:
        module: Module to read.
        index: What the rest of the tree declares for this module to read.
        enums: Members of every enum a lookup part can name.
        receiver_type: Simple name of the type a lookup is written on.
        separator: String standing between the parts of a composed value.

    Returns:
        List[LookupSite]: The lookups, in source order per scope.
    """
    sites: List[LookupSite] = []
    for scope in module_scopes(module.tree, imported_item_types=index.item_types):
        receivers = scope.environment.spellings_of(receiver_type)
        if not receivers:
            continue

        resolver = ValueResolver(
            environment=scope.environment,
            enums=enums,
            constants=index.constants,
        )
        sites.extend(lookup_site(module, site, resolver, separator) for site in find_subscripts(scope.node, receivers))

    return sites


def tree_lookups(
    modules: Iterable[SourceModule],
    *,
    index: SourceIndex,
    enums: EnumTable,
    receiver_type: str,
    separator: str,
) -> List[LookupSite]:
    """Every lookup a tree of modules writes on a receiver of the named type.

    Args:
        modules: Modules to read.
        index: What the tree declares, as `source_index` states it.
        enums: Members of every enum a lookup part can name.
        receiver_type: Simple name of the type a lookup is written on.
        separator: String standing between the parts of a composed value.

    Returns:
        List[LookupSite]: The lookups, module by module.
    """
    return [
        site
        for module in modules
        for site in module_lookups(
            module,
            index=index,
            enums=enums,
            receiver_type=receiver_type,
            separator=separator,
        )
    ]
