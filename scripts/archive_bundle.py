import argparse
import sys
import zipfile
from pathlib import Path
from typing import Final, List, Sequence

from bootstrap.layout import BUNDLES, DISTRIBUTION, repository_root
from bootstrap.project import Project, read_project

ARCHIVE_COMPRESSION: Final[int] = zipfile.ZIP_DEFLATED
ARCHIVE_SUFFIX: Final[str] = ".zip"


def archive_root(project: Project, label: str) -> str:
    """The directory every archived entry sits under, which names the archive too.

    Args:
        project: The project, whose name and version lead the name.
        label: The platform the bundle was built for, such as ``windows-x86_64``.

    Returns:
        str: The name, such as ``sampletones-v0.3.0-windows-x86_64``.
    """
    return f"{project.name}-v{project.version}-{label}"


def bundle_entries(source: Path) -> List[Path]:
    """Every file and directory inside a built bundle, ordered so repeated runs archive alike."""
    return sorted(source.rglob("*"))


def archive_name(path: Path, *, source: Path, root: str) -> str:
    """The location a bundle path takes inside the archive, gathered under a single root directory."""
    return f"{root}/{path.relative_to(source).as_posix()}"


def write_archive(source: Path, archive: Path, *, root: str) -> List[Path]:
    """Archives a built bundle directory, placing every entry under ``root``.

    Each entry is read where it lies, which keeps the archive available while a virus scanner or a
    process that ran the executable holds a handle inside the directory, and carries over the
    permission bits that let the launcher run once the archive is extracted.
    """
    archive.parent.mkdir(parents=True, exist_ok=True)
    entries = bundle_entries(source)
    with zipfile.ZipFile(archive, "w", ARCHIVE_COMPRESSION) as bundle:
        for path in entries:
            bundle.write(path, archive_name(path, source=source, root=root))

    return entries


def main(argv: Sequence[str]) -> int:
    """Archives the release bundle into the bundles directory, named by the version and the platform."""
    parser = argparse.ArgumentParser(description="Archive the release bundle under a versioned root.")
    parser.add_argument("--label", required=True, help="the platform the bundle was built for, such as windows-x86_64")
    arguments = parser.parse_args(list(argv))

    root = repository_root()
    project = read_project(root)
    source = root / DISTRIBUTION / project.name
    if not source.is_dir():
        print(f"::error::Bundle directory {source} is missing")
        return 1

    name = archive_root(project, arguments.label)
    archive = root / BUNDLES / f"{name}{ARCHIVE_SUFFIX}"
    entries = write_archive(source, archive, root=name)
    print(f"Archived {len(entries)} entries from {source} into {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
