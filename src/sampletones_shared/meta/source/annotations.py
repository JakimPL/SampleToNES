import ast
from typing import Final, FrozenSet, Optional, Tuple

from sampletones_shared.meta.source.nodes import slice_elements, terminal_name

ANNOTATION_WRAPPERS: Final[FrozenSet[str]] = frozenset({"Annotated", "ClassVar", "Final", "Optional"})


def _parse_annotation(text: str) -> Optional[ast.expr]:
    try:
        return ast.parse(text, mode="eval").body
    except SyntaxError:
        return None


def unwrap_annotation(annotation: Optional[ast.expr]) -> Optional[ast.expr]:
    """The type an annotation states, reached through the wrappers around it.

    `Final[X]`, `Optional[X]`, `ClassVar[X]`, `Annotated[X, ...]`, and the quoted form `"X"` all
    state `X`, and a nest of them unwraps to the same.

    Args:
        annotation: Annotation node to unwrap.

    Returns:
        Optional[ast.expr]: The innermost annotation, or `None` where there is none to read.
    """
    match annotation:
        case ast.Constant(value=str() as text):
            return unwrap_annotation(_parse_annotation(text))
        case ast.Subscript(value=value) as subscript if terminal_name(value) in ANNOTATION_WRAPPERS:
            return unwrap_annotation(slice_elements(subscript)[0])
        case _:
            return annotation


def annotation_type_name(annotation: Optional[ast.expr]) -> Optional[str]:
    """The simple name of the type an annotation states.

    A subscripted generic states its own name, so `Dict[str, int]` states `Dict`, while
    `Optional[LanguageManager]` states `LanguageManager`.

    Args:
        annotation: Annotation node to read.

    Returns:
        Optional[str]: The type name, or `None` where the annotation names none.
    """
    match unwrap_annotation(annotation):
        case ast.Subscript(value=value):
            return terminal_name(value)
        case ast.expr() as node:
            return terminal_name(node)
        case _:
            return None


def annotation_item_types(annotation: Optional[ast.expr]) -> Tuple[str, ...]:
    """The type names a container annotation states for what it holds.

    `Dict[ExportFormat, FileFilterElements]` states its key type and then its value type, and
    `Tuple[MenuElements, ...]` states its item type.

    Args:
        annotation: Annotation node to read.

    Returns:
        Tuple[str, ...]: The item type names, in the order the annotation writes them, holding an
            entry for each argument that names a type.
    """
    unwrapped = unwrap_annotation(annotation)
    if not isinstance(unwrapped, ast.Subscript):
        return ()

    names = (annotation_type_name(element) for element in slice_elements(unwrapped))
    return tuple(name for name in names if name is not None)
