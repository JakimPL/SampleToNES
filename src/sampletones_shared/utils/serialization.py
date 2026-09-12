import base64
import json
from contextlib import suppress
from pathlib import Path
from typing import Any, Dict, Final, List, Mapping, Optional, Type, TypeVar, Union

import numpy as np
import yaml
from pydantic import BaseModel

from sampletones_shared.types.array import Array
from sampletones_shared.types.data import SerializedData
from sampletones_shared.types.path import Pathlike

JSON_INDENT: Final[int] = 2
YAML_ROOT_STEM: Final[str] = "root"

ModelTypeT = TypeVar("ModelTypeT", bound=BaseModel)


def dump(data: Any) -> str:
    """
    Serializes data to a compact JSON string using `,` and `:` separators.
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
    """
    Saves data to a YAML file atomically via a temporary file.

    The data is written to a sibling ``.tmp`` file and then moved into place with a
    single ``replace``, so the target file updates only once the whole write
    succeeds. The temporary file is removed if the write fails.

    Args:
        filepath (Pathlike): Path to the output YAML file.
        data (Union[List[Any], SerializedData]): The data to save. Must be YAML-serializable.
    """
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


def load_yaml_model(
    filepath: Pathlike,
    model_type: Type[ModelTypeT],
    *,
    context: Optional[Mapping[str, Any]] = None,
) -> ModelTypeT:
    """
    Loads and validates a Pydantic model from a YAML file holding a mapping.

    Args:
        filepath (Pathlike): Path to the YAML file to load.
        model_type (Type[ModelTypeT]): Model class validating the mapping.
        context (Optional[Mapping[str, Any]]): Validation context forwarded to
            ``model_validate``, letting field validators resolve against shared state
            (e.g. a palette for color references).

    Returns:
        ModelTypeT: The validated model instance.

    Raises:
        TypeError: If the file holds anything other than a mapping.
    """
    raw = load_yaml(filepath)
    if not isinstance(raw, dict):
        raise TypeError(f"YAML file {filepath} must contain a mapping, got {type(raw)}")

    return model_type.model_validate(raw, context=context)


def load_yaml_model_dir(
    directory: Pathlike,
    model_type: Type[ModelTypeT],
    *,
    context: Optional[Mapping[str, Any]] = None,
) -> ModelTypeT:
    """
    Loads and validates a Pydantic model from a directory of YAML fragments.

    Each ``<field>.yaml`` file supplies the value for the model's top-level ``<field>``,
    so the directory layout mirrors the model's structure one file per field. A file
    named ``root.yaml`` holds a mapping whose entries become top-level fields directly,
    carrying the loose scalar fields that own no section file of their own.

    Args:
        directory (Pathlike): Directory holding the YAML fragment files.
        model_type (Type[ModelTypeT]): Model class validating the merged mapping.
        context (Optional[Mapping[str, Any]]): Validation context forwarded to
            ``model_validate``, letting field validators resolve against shared state
            (e.g. a palette for color references).

    Returns:
        ModelTypeT: The validated model instance.

    Raises:
        TypeError: If ``root.yaml`` holds anything other than a mapping.
    """
    merged: Dict[str, Any] = {}
    for path in sorted(Path(directory).glob("*.yaml")):
        content = load_yaml(path)
        if path.stem == YAML_ROOT_STEM:
            if not isinstance(content, dict):
                raise TypeError(f"YAML file {path} must contain a mapping, got {type(content)}")
            merged.update(content)
        else:
            merged[path.stem] = content

    return model_type.model_validate(merged, context=context)


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
