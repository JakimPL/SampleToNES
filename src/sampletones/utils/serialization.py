import base64
import hashlib
import json
from pathlib import Path
from typing import Any, Optional, Union

import flatbuffers
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


def snake_to_camel(snake_str: str) -> str:
    parts = snake_str.split("_")
    return "".join(word.capitalize() for word in parts)


def read_string_from_table(table_object: flatbuffers.table.Table, field_index: int) -> Optional[str]:
    buffer = table_object.Bytes
    position = table_object.Pos
    relative_offset = table_object.Offset(field_index)
    if relative_offset == 0:
        return None

    string_object_position = relative_offset + position
    string_length = int.from_bytes(buffer[string_object_position : string_object_position + 4], "little")
    print(string_length)

    return buffer[string_object_position + 4 : string_object_position + 4 + string_length].decode("utf-8")
