import hashlib
from collections.abc import Hashable
from typing import Final

from pydantic import BaseModel

from sampletones_shared.types.data import ModelHashable
from sampletones_shared.utils.serialization import dump

HASH_LENGTH: Final[int] = 32
HASH_PATTERN: Final[str] = rf"^[0-9a-f]{{{HASH_LENGTH}}}$"
IDENTITY_SEPARATOR: Final[str] = "\x00"


def get_hash_bytes(data: Hashable) -> bytes:
    """
    Converts hashable data types to signed bytes.

    Args:
        data (Hashable): The data to convert. Must be hashable.

    Returns:
        bytes: Byte representation of the data.

    Raises:
        TypeError: If the data is not hashable.
    """
    if not isinstance(data, Hashable):
        raise TypeError("Data must be hashable to convert to hash bytes")

    signed = hash(data)
    unsigned = signed & ((1 << 64) - 1)
    return unsigned.to_bytes(8, byteorder="big", signed=False)


def calculate_hash(data: ModelHashable, *, length: int = HASH_LENGTH) -> str:
    """
    Calculates a SHA-256 hash for hashable data types.

    Supports BaseModel instances, primitive types (bool, int, float, bytes, str),
    and other hashable objects. BaseModel instances are serialized to JSON before hashing.

    Args:
        data (ModelHashable): The data to hash. Can be BaseModel, bool, int, float,
            bytes, str, or any hashable object.
        length (int): The length of the hash string to return. Defaults to 32.

    Returns:
        str: Hexadecimal hash string truncated to the specified length.

    Raises:
        ValueError: If the length lies outside 1 to 64.
    """
    if length <= 0 or length > 64:
        raise ValueError("Hash length must be between 1 and 64")

    raw: bytes
    if isinstance(data, BaseModel):
        raw = dump(data.model_dump()).encode("utf-8")
    elif isinstance(data, (bool, int, float, bytes, str)):
        if not data:
            data = ""

        if isinstance(data, (bool, int, float)):
            data = str(float(data))

        if isinstance(data, str):
            data = data.encode("utf-8")

        raw = data
    else:
        raw = get_hash_bytes(data)

    return hashlib.sha256(raw).hexdigest()[:length]


def hash_models(*models: BaseModel, length: int = HASH_LENGTH) -> str:
    """
    Calculates a combined hash for multiple BaseModel instances.

    Models are serialized to JSON as a list and hashed together, ensuring
    the hash depends on both the models' content and their order.

    Args:
        *models (BaseModel): One or more BaseModel instances to hash.
        length (int): The length of the hash string to return. Defaults to 32.

    Returns:
        str: Hexadecimal hash string representing all models combined.
    """
    combined = [model.model_dump() for model in models]
    json_string = dump(combined)
    return calculate_hash(json_string, length=length)


def hash_model(model: BaseModel, *, length: int = HASH_LENGTH) -> str:
    """
    Calculates a hash for a single BaseModel instance.

    Args:
        model (BaseModel): The BaseModel instance to hash.
        length (int): The length of the hash string to return. Defaults to 32.

    Returns:
        str: Hexadecimal hash string representing the model.
    """
    return hash_models(model, length=length)


def identity_digest(*parts: str, length: int = HASH_LENGTH) -> str:
    """
    Calculates a hash for an identity spelled out in parts.

    The parts are joined on a separator that names carry nowhere, so one identity reaches
    one digest and two identities spelled in different parts reach different digests.

    Args:
        *parts (str): The pieces the identity is spelled in, in the order they belong.
        length (int): The length of the hash string to return. Defaults to 32.

    Returns:
        str: Hexadecimal hash string representing the identity.
    """
    return calculate_hash(IDENTITY_SEPARATOR.join(parts), length=length)
