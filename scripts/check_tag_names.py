import ast
import sys
from pathlib import Path
from typing import Final, List, Optional

from sampletones_application.categories.hierarchy import Page, Panel, Widget
from sampletones_application.categories.key.tag import TagName
from sampletones_application.tags.compose import TAG_SEPARATOR

TAG_PREFIX: Final = "TAG"
TAG_NAME_CLASS_NAME: Final = "TagName"

ARGUMENT_ENUMS: Final = (Page, Panel, Widget)


def expected_name(tag: TagName) -> str:
    body = str(tag).upper().replace(TAG_SEPARATOR, "_")
    return f"{TAG_PREFIX}_{body}"


def validate_assignment(assignment: ast.Assign, path: Path) -> Optional[str]:
    (target,) = assignment.targets
    if (
        not isinstance(assignment.value, ast.Call)
        or not isinstance(assignment.value.func, ast.Name)
        or assignment.value.func.id != TAG_NAME_CLASS_NAME
    ):
        return None

    if not isinstance(target, ast.Name):
        return f"Module '{path.name}' contains an invalid tag:\n{str(type(target))}, expected ast.Name"

    page, panel, widget, name = assignment.value.args
    if (
        not isinstance(page, ast.Attribute)
        or not isinstance(panel, ast.Attribute)
        or not isinstance(widget, ast.Attribute)
    ):
        return f"Module '{path.name}' contains an invalid tag: {target.id},\nexpected all arguments to be ast.Attribute"

    if not isinstance(name, ast.Constant) or not isinstance(name.value, str):
        return (
            f"Module '{path.name}' contains an invalid tag: {target.id},\n"
            "expected last argument to be ast.Constant with a string value"
        )

    page_value, panel_value, widget_value = (
        getattr(enum, attribute.attr) for enum, attribute in zip(ARGUMENT_ENUMS, (page, panel, widget))
    )
    tag = TagName(page_value, panel_value, widget_value, name.value)
    expected = expected_name(tag)
    if target.id != expected:
        return f"Module '{path.name}' contains an invalid tag: {target.id},\nexpected {expected}"

    return None


def validate_source_file(path: Path) -> List[str]:
    tree = ast.parse(path.read_text())
    messages: List[str] = []
    assignments = [item for item in tree.body if isinstance(item, ast.Assign)]
    for assignment in assignments:
        message = validate_assignment(assignment, path)
        if message:
            messages.append(message)

    return messages


def validate_tag_names(paths: List[Path]) -> List[str]:
    invalid_tags = []
    for path in paths:
        invalid_tags.extend(validate_source_file(path))

    return invalid_tags


if __name__ == "__main__":
    args = sys.argv[1:]
    filepaths = [Path(argument) for argument in args]
    invalid_tags = validate_tag_names(filepaths)
    if not invalid_tags:
        sys.exit(0)

    for invalid_tag in invalid_tags:
        print(invalid_tag)

    sys.exit(1)
