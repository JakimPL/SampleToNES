import json
from typing import Any, Dict, Final, List, NamedTuple, Optional, Tuple

import msgpack

from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.compatibility.library import UPDATES as LIBRARY_UPDATES
from sampletones_core.compatibility.project import UPDATES as PROJECT_UPDATES
from sampletones_core.compatibility.reconstruction import UPDATES as RECONSTRUCTION_UPDATES
from sampletones_core.compatibility.update import VersionUpdate
from sampletones_shared.application import (
    SAMPLETONES_LIBRARY_DATA_VERSION,
    SAMPLETONES_PROJECT_DATA_VERSION,
    SAMPLETONES_RECONSTRUCTION_DATA_VERSION,
)
from sampletones_shared.deployment.version import Version, compare_versions
from sampletones_shared.types.data import SerializedData

CURRENT_VERSIONS: Final[Dict[ObjectKind, str]] = {
    ObjectKind.LIBRARY: SAMPLETONES_LIBRARY_DATA_VERSION,
    ObjectKind.RECONSTRUCTION: SAMPLETONES_RECONSTRUCTION_DATA_VERSION,
    ObjectKind.PROJECT: SAMPLETONES_PROJECT_DATA_VERSION,
}

UPDATES: Final[Dict[ObjectKind, Tuple[VersionUpdate, ...]]] = {
    ObjectKind.LIBRARY: LIBRARY_UPDATES,
    ObjectKind.RECONSTRUCTION: RECONSTRUCTION_UPDATES,
    ObjectKind.PROJECT: PROJECT_UPDATES,
}


class _VersionPath(NamedTuple):
    """Where a format stores its version: the section enclosing the field, and the field itself."""

    section: Optional[str]
    field: str


def upgrade(
    kind: ObjectKind,
    version: str,
    data: SerializedData,
    updates: Tuple[VersionUpdate, ...],
    current_version: str,
) -> SerializedData:
    """Brings one format's serialized data to the version this build reads and writes.

    A format stores the version its file was written at; the load path hands that
    version and the payload here before deserialization, so a file written by an
    older build loads correctly even after the format's stored shape changed.

    The engine walks the registered steps of ``kind``, applying the step whose
    base version matches the position reached, until ``current_version`` is met.
    The walk follows these rules:

    - a step runs only inside a complete path from ``version`` to
      ``current_version``; when a position has no continuing step, the data
      comes back unchanged and the format's load contract refuses the file, the
      same outcome as for any version this build does not support;
    - each step transforms the payload the previous step produced;
    - a walk that ran stamps the format's version field with ``current_version``,
      so the data states the version its shape now matches and a later save
      writes that version;
    - data already at ``current_version`` returns as the same object, which is
      how the byte-level wrappers keep their path of skipping re-encoding.

    Args:
        kind: The format whose update chain applies.
        version: The version the data states.
        data: The serialized data to upgrade.
        updates: The registered steps for the format.
        current_version: The version this build reads and writes.

    Returns:
        SerializedData: The data upgraded and stamped with ``current_version``,
        or the input unchanged when the chain does not reach it.
    """
    chain = _resolve_chain(
        version,
        updates,
        current_version,
    )

    if not chain:
        return data

    upgraded = data
    for update in chain:
        upgraded = update.apply(upgraded)

    return _stamp(kind, upgraded, current_version)


def upgrade_binary(kind: ObjectKind, binary: bytes) -> bytes:
    """Upgrades a msgpack payload at the load boundary of a binary format.

    The reconstruction and library formats store their data as msgpack mappings
    whose ``metadata`` section carries ``<kind>_data_version``. This wrapper
    unpacks the payload, reads that version, runs :func:`upgrade`, and re-encodes
    the upgraded mapping. It returns the input bytes unchanged whenever the
    payload stays as it is: when it does not unpack to a mapping, when it lacks
    the version field, or when the chain does not apply.
    """
    try:
        data = msgpack.unpackb(binary, raw=False)
    except ValueError:
        return binary

    upgraded = _upgrade_payload(kind, data)
    if upgraded is None:
        return binary

    return bytes(msgpack.packb(upgraded, use_bin_type=True))


def upgrade_json(kind: ObjectKind, raw: bytes) -> bytes:
    """Upgrades a JSON document at the load boundary of a JSON format.

    The project format stores ``format_version`` at the document root. This
    wrapper parses the document, reads that version, runs :func:`upgrade`, and
    re-encodes the upgraded document. It returns the input bytes unchanged
    whenever the document stays as it is: when it does not parse to a mapping,
    when it lacks the version field, or when the chain does not apply.
    """
    try:
        data = json.loads(raw)
    except ValueError:
        return raw

    upgraded = _upgrade_payload(kind, data)
    if upgraded is None:
        return raw

    return json.dumps(upgraded).encode("utf-8")


def _upgrade_kind(
    kind: ObjectKind,
    version: str,
    data: SerializedData,
) -> SerializedData:
    return upgrade(
        kind,
        version,
        data,
        UPDATES[kind],
        CURRENT_VERSIONS[kind],
    )


def _upgrade_payload(
    kind: ObjectKind,
    payload: Any,
) -> Optional[SerializedData]:
    """Runs the format's chain over a parsed payload.

    Returns the upgraded mapping, or ``None`` when the payload stays as it is:
    when it is not a mapping, when it lacks the format's version field, or when
    the chain does not apply.
    """
    if not isinstance(payload, dict):
        return None

    version = _read_version(kind, payload)
    if version is None:
        return None

    upgraded = _upgrade_kind(kind, version, payload)
    return None if upgraded is payload else upgraded


def _version_path(kind: ObjectKind) -> _VersionPath:
    if kind is ObjectKind.PROJECT:
        return _VersionPath(
            section=None,
            field="format_version",
        )

    return _VersionPath(
        section="metadata",
        field=f"{kind.value}_data_version",
    )


def _read_version(kind: ObjectKind, data: SerializedData) -> Optional[str]:
    path = _version_path(kind)
    section_name = path.section
    if section_name is None:
        value = data.get(path.field)
    else:
        section = data.get(section_name)
        if not isinstance(section, dict):
            return None

        value = section.get(path.field)

    return value if isinstance(value, str) else None


def _stamp(
    kind: ObjectKind,
    data: SerializedData,
    version: str,
) -> SerializedData:
    path = _version_path(kind)
    stamped = dict(data)
    section_name = path.section
    if section_name is None:
        stamped[path.field] = version
        return stamped

    section = data.get(section_name)
    if isinstance(section, dict):
        stamped[section_name] = {**section, path.field: version}

    return stamped


def _resolve_chain(
    version: str,
    updates: Tuple[VersionUpdate, ...],
    current_version: str,
) -> Tuple[VersionUpdate, ...]:
    by_base: Dict[str, VersionUpdate] = {}
    for update in updates:
        base = _canonical(str(update.base))
        if base in by_base:
            raise ValueError(f"Duplicate base version {base} among registered updates")

        by_base[base] = update

    chain: List[VersionUpdate] = []
    position = _canonical(version)
    for _ in range(len(updates) + 1):
        if compare_versions(position, current_version) == 0:
            return tuple(chain)

        matching = by_base.get(position)
        if matching is None:
            return ()

        chain.append(matching)
        position = _canonical(str(matching.target))

    return ()


def _canonical(version: str) -> str:
    return str(Version.model_validate(version))
