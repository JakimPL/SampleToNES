import ast
import sys
from pathlib import Path
from typing import Final, List, Optional

TAG_PREFIX: Final = "TAG"
TAG_NAME_CLASS_NAME: Final = "TagName"


def validate_assignment(assignment: ast.Assign, path: Path) -> Optional[str]:
    (target,) = assignment.targets
    if (
        not isinstance(assignment.value, ast.Call)
        or not isinstance(assignment.value.func, ast.Name)
        or assignment.value.func.id != TAG_NAME_CLASS_NAME
    ):
        return None

    elif not isinstance(target, ast.Name):
        return f"Module '{path.name}' contains an invalid tag:\n{str(type(target))}, expected ast.Name"

    page, panel, widget, name = assignment.value.args
    if (
        not isinstance(page, ast.Attribute)
        or not isinstance(panel, ast.Attribute)
        or not isinstance(widget, ast.Attribute)
    ):
        return f"Module '{path.name}' contains an invalid tag: {target.id},\nexpected all arguments to be ast.Attribute"

    elif not isinstance(name, ast.Constant) or not isinstance(name.value, str):
        return f"Module '{path.name}' contains an invalid tag: {target.id},\nexpected last argument to be ast.Constant with a string value"

    items = TAG_PREFIX, page.attr, panel.attr, widget.attr, name.value.upper()
    expected_name = "_".join(items)

    if target.id != expected_name:
        return f"Module '{path.name}' contains an invalid tag: {target.id},\nexpected {expected_name}"

    return None


def validate_source_file(path: Path) -> Optional[List[str]]:
    with open(path, "r") as file:
        source = file.read()

    messages: List[str] = []
    tree = ast.parse(source)
    assignments = [item for item in tree.body if isinstance(item, ast.Assign)]
    for assignment in assignments:
        message = validate_assignment(assignment, path)
        if message:
            messages.append(message)

    return messages


def validate_tag_names(paths: List[Path]) -> List[str]:
    invalid_tags = []
    for path in paths:
        messages = validate_source_file(path)
        if messages:
            invalid_tags.extend(messages)

    return invalid_tags


if __name__ == "__main__":
    args = sys.argv[1:]
    filepaths = [Path(argument) for argument in args]
    invalid_tags = validate_tag_names(filepaths)
    if not invalid_tags:
        sys.exit(0)

    for tag in invalid_tags:
        print(tag)

    sys.exit(1)
