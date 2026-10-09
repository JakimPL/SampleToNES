import argparse
import sys
import zipfile
from pathlib import Path
from typing import Final, List, Sequence

from bootstrap.layout import BUNDLES, DISTRIBUTION, repository_root
from bootstrap.platforms.factory import current_platform
from bootstrap.platforms.protocol import Platform
from bootstrap.project import Project, read_project

ARCHIVE_COMPRESSION: Final[int] = zipfile.ZIP_DEFLATED
ARCHIVE_SUFFIX: Final[str] = ".zip"


def archive_root(project: Project, label: str) -> str:
    """The directory every archived entry sits under, which names the archive too.

    Args:
        project: The project, whose name and release tag lead the name.
        label: The platform the bundle was built for, such as ``windows-x86_64``.

    Returns:
        str: The name, such as ``sampletones-v0.3.0-windows-x86_64``.
    """
    return f"{project.name}-{project.tag}-{label}"


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


def archive_release(root: Path, platform: Platform, *, label: str) -> int:
    """Archives the release bundle built under ``root`` into its bundles directory.

    Args:
        root: The repository the bundle was built in.
        platform: The system the bundle was built for, which places the bundle's directory.
        label: The platform's name in the archive, such as ``windows-x86_64``.

    Returns:
        int: ``0`` once the archive is written, ``1`` where the release bundle is missing.

    Raises:
        SystemExit: If the system builds no bundle.
    """
    project = read_project(root)
    source = platform.bundling().launcher(root / DISTRIBUTION, name=project.name, release=True).parent
    if not source.is_dir():
        print(f"::error::Bundle directory {source} is missing")
        return 1

    name = archive_root(project, label)
    archive = root / BUNDLES / f"{name}{ARCHIVE_SUFFIX}"
    entries = write_archive(source, archive, root=name)
    print(f"Archived {len(entries)} entries from {source} into {archive}")
    return 0


def main(argv: Sequence[str]) -> int:
    """Archives the release bundle into the bundles directory, named by the version and the platform."""
    parser = argparse.ArgumentParser(description="Archive the release bundle under a versioned root.")
    parser.add_argument("--label", required=True, help="the platform the bundle was built for, such as windows-x86_64")
    arguments = parser.parse_args(list(argv))

    return archive_release(repository_root(), current_platform(), label=arguments.label)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
