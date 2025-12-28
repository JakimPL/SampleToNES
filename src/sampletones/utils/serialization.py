import base64
import hashlib
import json
from typing import Any

import numpy as np
import yaml
from pydantic import BaseModel

from sampletones.typehints import Pathlike, SerializedData

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


def hash_models(*models: BaseModel, length: int = 32) -> str:
    combined = [model.model_dump() for model in models]
    json_string = dump(combined)
    return hashlib.sha256(json_string.encode("utf-8")).hexdigest()[:length]


def hash_model(model: BaseModel, length: int = 32) -> str:
    return hash_models(model, length=length)


def snake_to_camel(snake_str: str) -> str:
    parts = snake_str.split("_")
    return "".join(word.capitalize() for word in parts)
