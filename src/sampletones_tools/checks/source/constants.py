import ast
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class ModuleConstant:
    """A module-level name bound to a value, as one statement spells the binding."""

    name: str
    value: ast.expr
    annotation: Optional[ast.expr]
    line: int


def module_constants(tree: ast.Module) -> List[ModuleConstant]:
    """The bindings a module makes to a plain name at its top level.

    Both `NAME = value` and `NAME: Annotation = value` are reported, and a chained
    `FIRST = SECOND = value` yields one entry per name it binds.

    Args:
        tree: Parsed module to read.

    Returns:
        List[ModuleConstant]: The bindings, in source order.
    """
    constants: List[ModuleConstant] = []
    for statement in tree.body:
        match statement:
            case ast.Assign(targets=targets, value=value):
                constants.extend(
                    ModuleConstant(
                        name=target.id,
                        value=value,
                        annotation=None,
                        line=statement.lineno,
                    )
                    for target in targets
                    if isinstance(target, ast.Name)
                )
            case ast.AnnAssign(target=ast.Name(id=name), annotation=annotation, value=ast.expr() as value):
                constants.append(
                    ModuleConstant(
                        name=name,
                        value=value,
                        annotation=annotation,
                        line=statement.lineno,
                    )
                )

    return constants
