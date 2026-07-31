import argparse
import sys
import zipfile
from pathlib import Path
from typing import Final, List, Sequence

ARCHIVE_COMPRESSION: Final[int] = zipfile.ZIP_DEFLATED


def bundle_entries(source: Path) -> List[Path]:
    """Every file and directory inside a built bundle, ordered so repeated runs archive alike."""
    return sorted(source.rglob("*"))


def archive_name(path: Path, *, source: Path, root: str) -> str:
    """The location a bundle path takes inside the archive, gathered under a single root directory."""
    return f"{root}/{path.relative_to(source).as_posix()}"


def write_archive(source: Path, archive: Path, *, root: str) -> List[Path]:
    """Archive a built bundle directory, placing every entry under ``root``.

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
    """Archive a built bundle directory under a versioned root directory."""
    parser = argparse.ArgumentParser(description="Archive a built bundle directory under a versioned root.")
    parser.add_argument("source", type=Path, help="the built bundle directory, such as bin/sampletones")
    parser.add_argument("archive", type=Path, help="the path of the zip file to write")
    parser.add_argument("--root", required=True, help="the directory name every archived entry sits under")
    arguments = parser.parse_args(list(argv))

    source: Path = arguments.source
    archive: Path = arguments.archive
    if not source.is_dir():
        print(f"::error::Bundle directory {source} is missing")
        return 1

    entries = write_archive(source, archive, root=arguments.root)
    print(f"Archived {len(entries)} entries from {source} into {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
