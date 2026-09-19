from typing import FrozenSet

import msgpack

from sampletones_shared.types.data import SerializedData
from sampletones_shared.types.path import Pathlike


def read_leading_fields(path: Pathlike, names: FrozenSet[str]) -> SerializedData:
    """The named top-level fields of a stored document, read from the front of its file.

    A stored :class:`DataModel` is one map whose fields follow the model's declaration order, so
    the fields a model declares first sit in the first bytes of the file. The read decodes those
    fields and steps over any other in its way, and it ends once every named field is found, which
    keeps it to the front of the file however large the rest is. A file whose front decodes as no
    map reads as holding none of the fields.

    Args:
        path: The stored document.
        names: The top-level fields to read.

    Returns:
        SerializedData: Each named field the file holds, as stored.
    """
    found: SerializedData = {}
    with open(path, "rb") as file:
        unpacker = msgpack.Unpacker(file, raw=False)
        try:
            for _ in range(unpacker.read_map_header()):
                name = unpacker.unpack()
                if not isinstance(name, str) or name not in names:
                    unpacker.skip()
                    continue

                found[name] = unpacker.unpack()
                if len(found) == len(names):
                    break
        except (ValueError, msgpack.OutOfData):
            return {}

    return found
