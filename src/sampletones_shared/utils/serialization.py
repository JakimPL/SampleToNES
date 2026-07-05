import base64
import hashlib
import json
from collections.abc import Hashable
from contextlib import suppress
from pathlib import Path
from typing import Any, Final, List, Type, TypeVar, Union

import numpy as np
import yaml
from pydantic import BaseModel

from sampletones_shared.types.array import Array
from sampletones_shared.types.data import ModelHashable, SerializedData
from sampletones_shared.types.path import Pathlike

JSON_INDENT: Final[int] = 2
HASH_LENGTH: Final[int] = 32
HASH_PATTERN: Final[str] = rf"^[0-9a-f]{{{HASH_LENGTH}}}$"

ModelTypeT = TypeVar("ModelTypeT", bound=BaseModel)


def dump(data: Any) -> str:
    """
    Serializes data to a compact JSON string without whitespace.
    Sorts keys to ensure consistent output for hashing.

    Args:
        data (Any): The data to serialize. Must be JSON-serializable.

    Returns:
        str: Compact JSON string representation of the data.
    """
    return json.dumps(
        data,
        separators=(",", ":"),
        sort_keys=True,
        indent=None,
    )


def save_json(filepath: Pathlike, data: Union[List[Any], SerializedData]) -> None:
    """
    Saves data to a JSON file with indentation for readability.

    Args:
        filepath (Pathlike): Path to the output JSON file.
        data (Union[List[Any], SerializedData]): The data to save. Must be JSON-serializable.
    """
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=JSON_INDENT)


def load_json(filepath: Pathlike) -> Union[List[Any], SerializedData]:
    """
    Loads data from a JSON file.

    Args:
        filepath (Pathlike): Path to the JSON file to load.

    Returns:
        Union[List[Any], SerializedData]: The deserialized data structure.
    """
    with open(filepath, "r", encoding="utf-8") as file:
        data: Union[List[Any], SerializedData] = json.load(file)
        return data


def save_yaml(filepath: Pathlike, data: Union[List[Any], SerializedData]) -> None:
    """
    Saves data to a YAML file.

    Args:
        filepath (Pathlike): Path to the output YAML file.
        data (Union[List[Any], SerializedData]): The data to save. Must be YAML-serializable.
    """
    with open(filepath, "w", encoding="utf-8") as file:
        yaml.dump(data, file)


def save_yaml_atomic(filepath: Pathlike, data: Union[List[Any], SerializedData]) -> None:
    path = Path(filepath)
    tmp = path.with_suffix(".tmp")
    try:
        save_yaml(tmp, data)
        tmp.replace(path)
    except Exception:
        with suppress(FileNotFoundError):
            tmp.unlink()
        raise


def load_yaml(filepath: Pathlike) -> Union[List[Any], SerializedData]:
    """
    Loads data from a YAML file using safe loading.

    Args:
        filepath (Pathlike): Path to the YAML file to load.

    Returns:
        Union[List[Any], SerializedData]: The deserialized data structure.
    """
    with open(filepath, "r", encoding="utf-8") as file:
        data: SerializedData = yaml.safe_load(file)
        return data


def load_yaml_model(filepath: Pathlike, model_type: Type[ModelTypeT]) -> ModelTypeT:
    """
    Loads and validates a Pydantic model from a YAML file holding a mapping.

    Args:
        filepath (Pathlike): Path to the YAML file to load.
        model_type (Type[ModelTypeT]): Model class validating the mapping.

    Returns:
        ModelTypeT: The validated model instance.

    Raises:
        TypeError: If the file holds anything other than a mapping.
    """
    raw = load_yaml(filepath)
    if not isinstance(raw, dict):
        raise TypeError(f"YAML file {filepath} must contain a mapping, got {type(raw)}")

    return model_type.model_validate(raw)


def save_binary(filepath: Pathlike, data: bytes) -> None:
    """
    Saves binary data to a file.

    Args:
        filepath (Pathlike): Path to the output binary file.
        data (bytes): The binary data to save.
    """
    with open(filepath, "wb") as file:
        file.write(data)


def load_binary(filepath: Pathlike) -> bytes:
    """
    Loads binary data from a file.

    Args:
        filepath (Pathlike): Path to the binary file to load.

    Returns:
        bytes: The binary data from the file.
    """
    with open(filepath, "rb") as file:
        return file.read()


def serialize_array(array: Array) -> SerializedData:
    """
    Serializes a numpy array to a JSON-compatible dictionary.

    The array data is base64-encoded, and metadata (shape and dtype) is preserved
    to allow exact reconstruction.

    Args:
        array (Array): The numpy array to serialize.

    Returns:
        SerializedData: A dictionary containing:
            - data: Base64-encoded array bytes
            - shape: Original array shape as tuple
            - dtype: String representation of array dtype
    """
    return {
        "data": base64.b64encode(array.tobytes()).decode("utf-8"),
        "shape": array.shape,
        "dtype": str(array.dtype),
    }


def deserialize_array(data: SerializedData) -> np.ndarray:
    """
    Deserializes a numpy array from a dictionary created by `serialize_array`.

    Args:
        data (SerializedData): Dictionary containing:
            - data: Base64-encoded array bytes
            - shape: Array shape as tuple
            - dtype: String representation of array dtype

    Returns:
        np.ndarray: The reconstructed numpy array with original shape and dtype.
    """
    array_data = base64.b64decode(data["data"].encode("utf-8"))
    array = np.frombuffer(array_data, dtype=data["dtype"])
    return array.reshape(data["shape"])


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


def snake_to_camel(snake_str: str) -> str:
    """
    Converts a snake_case string to CamelCase.

    Args:
        snake_str (str): String in snake_case format.

    Returns:
        str: String converted to CamelCase.

    Examples:
        >>> snake_to_camel("hello_world")
        'HelloWorld'
        >>> snake_to_camel("my_variable_name")
        'MyVariableName'
        >>> snake_to_camel("single")
        'Single'
    """
    parts = snake_str.split("_")
    return "".join(word.capitalize() for word in parts)
