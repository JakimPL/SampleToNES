import base64
import hashlib
import json
from pathlib import Path
from typing import Any, Union

import numpy as np
import yaml
from pydantic import BaseModel

from sampletones.typehints import SerializedData

JSON_INDENT = 2


def dump(data: Any) -> str:
    return json.dumps(data, separators=(",", ":"))


def save_json(filepath: Union[str, Path], data: SerializedData) -> None:
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=JSON_INDENT)


def load_json(filepath: Union[str, Path]) -> SerializedData:
    with open(filepath, "r", encoding="utf-8") as file:
        return json.load(file)


def save_yaml(filepath: Union[str, Path], data: SerializedData) -> None:
    with open(filepath, "w", encoding="utf-8") as file:
        yaml.dump(data, file)


def load_yaml(filepath: Union[str, Path]) -> SerializedData:
    with open(filepath, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def save_binary(filepath: Union[str, Path], data: bytes) -> None:
    with open(filepath, "wb") as file:
        file.write(data)


def load_binary(filepath: Union[str, Path]) -> bytes:
    with open(filepath, "rb") as file:
        return file.read()


def serialize_array(array: np.ndarray) -> SerializedData:
    return {
        "data": base64.b64encode(array.tobytes()).decode("utf-8"),
        "shape": array.shape,
        "dtype": str(array.dtype),
    }


def deserialize_array(data: SerializedData) -> np.ndarray:
    array_data = base64.b64decode(data["data"].encode("utf-8"))
    array = np.frombuffer(array_data, dtype=data["dtype"])
    return array.reshape(data["shape"])


def hash_models(*models: BaseModel, length: int = 32) -> str:
    combined = [model.model_dump() for model in models]
    json_string = dump(combined)
    return hashlib.sha256(json_string.encode("utf-8")).hexdigest()[:length]


def hash_model(model: BaseModel, length: int = 32) -> str:
    return hash_models(model, length=length)


def snake_to_camel(snake_str: str) -> str:
    parts = snake_str.split("_")
    return "".join(word.capitalize() for word in parts)
