import base64
import hashlib
import json
import struct
from typing import Any

import numpy as np
import yaml
from pydantic import BaseModel

from sampletones.typehints import ModelHashable, Pathlike, SerializedData

JSON_INDENT = 2


def dump(data: Any) -> str:
    return json.dumps(data, separators=(",", ":"))


def save_json(filepath: Pathlike, data: SerializedData) -> None:
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=JSON_INDENT)


def load_json(filepath: Pathlike) -> SerializedData:
    with open(filepath, "r", encoding="utf-8") as file:
        data: SerializedData = json.load(file)
        return data


def save_yaml(filepath: Pathlike, data: SerializedData) -> None:
    with open(filepath, "w", encoding="utf-8") as file:
        yaml.dump(data, file)


def load_yaml(filepath: Pathlike) -> SerializedData:
    with open(filepath, "r", encoding="utf-8") as file:
        data: SerializedData = yaml.safe_load(file)
        return data


def save_binary(filepath: Pathlike, data: bytes) -> None:
    with open(filepath, "wb") as file:
        file.write(data)


def load_binary(filepath: Pathlike) -> bytes:
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


def calculate_hash(data: ModelHashable, length: int = 32) -> str:
    if isinstance(data, BaseModel):
        data = dump(data.model_dump())

    raw: bytes
    match data:
        case bytes():
            raw = data
        case str():
            raw = data.encode("utf-8")
        case float():
            raw = struct.pack("f", data)
        case int():
            raw = struct.pack("q", data)
        case bool():
            raw = struct.pack("?", data)
        case _:
            raise TypeError(f"Unsupported data type for hashing: {type(data)}")

    return hashlib.sha256(raw).hexdigest()[:length]


def hash_models(*models: BaseModel, length: int = 32) -> str:
    combined = [model.model_dump() for model in models]
    json_string = dump(combined)
    return calculate_hash(json_string, length=length)


def hash_model(model: BaseModel, length: int = 32) -> str:
    return hash_models(model, length=length)


def snake_to_camel(snake_str: str) -> str:
    parts = snake_str.split("_")
    return "".join(word.capitalize() for word in parts)
