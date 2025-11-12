import base64
import hashlib
import json
from pathlib import Path
from typing import Any, Union

import numpy as np
from pydantic import BaseModel

from sampletones.typehints import SerializedData

JSON_INDENT = 2


def dump(data: Any) -> str:
    return json.dumps(data, separators=(",", ":"))


def save_json(filepath: Union[str, Path], data: SerializedData) -> None:
    with open(filepath, "w") as file:
        json.dump(data, file, indent=JSON_INDENT)


def load_json(filepath: Union[str, Path]) -> SerializedData:
    with open(filepath, "r") as file:
        return json.load(file)


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
