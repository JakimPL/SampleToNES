from enum import StrEnum
from pathlib import Path
from types import ModuleType
from typing import Any, Self, TypeVar, Union, get_args, get_origin

import numpy as np
from flatbuffers.builder import Builder
from flatbuffers.table import Table
from pydantic import BaseModel

from sampletones.exceptions import DeserializationError, SerializationError
from sampletones.typehints import SerializedData
from sampletones.utils import load_binary, save_binary, snake_to_camel

FLOAT32_SIZE = 4


class DataModel(BaseModel):
    @classmethod
    def buffer_reader(cls) -> type:
        raise NotImplementedError("Subclasses must implement buffer_reader method")

    @classmethod
    def buffer_builder(cls) -> ModuleType:
        raise NotImplementedError("Subclasses must implement buffer_builder method")

    def serialize(self) -> bytes:
        builder = Builder(1024)
        offset = self._serialize_inner(builder)
        builder.Finish(offset)
        return bytes(builder.Output())

    @classmethod
    def deserialize(cls, buffer: bytes) -> Self:
        fb_reader = cls.buffer_reader()
        root = fb_reader.GetRootAs(buffer, 0)
        return cls._deserialize_inner(root)

    def save(self, path: Union[str, Path]) -> None:
        binary = self.serialize()
        save_binary(path, binary)

    @classmethod
    def load(cls, path: Union[str, Path]) -> Self:
        binary = load_binary(path)
        return cls.deserialize(binary)

    def _serialize_inner(self, builder: Builder) -> int:
        fb_builder = self.buffer_builder()
        offsets = {}

        for field_name in type(self).model_fields.keys():
            value = getattr(self, field_name)
            camel = snake_to_camel(field_name)
            add_method = f"Add{camel}"

            fb_add = getattr(fb_builder, add_method, None)
            if fb_add is None:
                raise AttributeError(f"{fb_builder.__name__} missing '{add_method}' for field '{field_name}'")

            if isinstance(value, DataModel):
                offsets[field_name] = value._serialize_inner(builder)

            elif isinstance(value, np.ndarray):
                offsets[field_name] = self._serialize_numpy_array(builder, value, field_name)

            elif isinstance(value, Path):
                offsets[field_name] = builder.CreateString(str(value))

            elif isinstance(value, list):
                offsets[field_name] = self._serialize_list(builder, value, field_name)

            elif isinstance(value, (str, StrEnum)):
                offsets[field_name] = self._serialize_string(builder, value)

            elif isinstance(value, (int, float, bool)):
                offsets[field_name] = value

            else:
                raise SerializationError(f"Unsupported field type {type(value)} for {field_name}")

        fb_builder.Start(builder)
        for field_name, val in offsets.items():
            camel = snake_to_camel(field_name)
            fb_add = getattr(fb_builder, f"Add{camel}")
            fb_add(builder, val)

        return fb_builder.End(builder)

    @classmethod
    def _deserialize_inner(cls, fb_object: Any) -> Self:
        field_values: SerializedData = {}

        for field_name, field_info in cls.model_fields.items():
            camel = snake_to_camel(field_name)
            getter = getattr(fb_object, camel, None)
            if getter is None:
                raise DeserializationError(f"{fb_object.__class__.__name__} missing getter '{camel}'")

            annotation = field_info.annotation
            if annotation is None:
                raise DeserializationError(f"Field '{field_name}' has no annotation")

            if annotation is np.ndarray:
                value = cls._deserialize_numpy_array(fb_object, field_name)

            elif annotation is Path:
                raw = getter().decode("utf-8")
                value = Path(raw)

            elif isinstance(annotation, TypeVar) or get_origin(annotation) is Union:
                table = getter()
                value = cls._deserialize_union(table, field_values)

            elif get_origin(annotation) is list:
                list_class = get_args(annotation)[0]
                value = cls._deserialize_list(fb_object, field_name, list_class)

            elif issubclass(annotation, DataModel):
                fb_child = getter()
                value = annotation._deserialize_inner(fb_child)

            elif issubclass(annotation, (str, StrEnum)):
                value = cls._deserialize_string(getter(), annotation)

            else:
                value = annotation(getter())

            field_values[field_name] = value

        return cls(**field_values)

    def _serialize_list(self, builder: Builder, collection: list, field_name: str) -> int:
        if len(collection) == 0:
            return 0

        elif all(isinstance(value, (int, float)) for value in collection):
            return self._serialize_numpy_array(builder, np.array(collection, dtype=np.float32), field_name)

        elif all(isinstance(value, (str, StrEnum)) for value in collection):
            string_offsets = [self._serialize_string(builder, value) for value in collection]
            return self._prepend_offsets(builder, string_offsets)

        elif all(isinstance(model, DataModel) for model in collection):
            child_offsets = [model._serialize_inner(builder) for model in collection]
            return self._prepend_offsets(builder, child_offsets)

        raise SerializationError(
            f"Unsupported list element type {type(collection[0])} or mixed types for field '{field_name}'"
        )

    def _serialize_string(self, builder: Builder, value: Union[str, StrEnum]) -> int:
        if isinstance(value, StrEnum):
            value = value.value
        return builder.CreateString(value)

    @classmethod
    def _deserialize_string(cls, raw: bytes, string_class: type) -> Union[str, StrEnum]:
        string = raw.decode("utf-8")
        if issubclass(string_class, StrEnum):
            return string_class(string)
        return string

    @classmethod
    def _deserialize_list(cls, fb_object: Any, field_name: str, element_class: type) -> np.ndarray | list:
        camel = snake_to_camel(field_name)
        getter = getattr(fb_object, camel, None)
        length_function = getattr(fb_object, f"{camel}Length", None)

        origin = get_origin(element_class)
        if origin is not None:
            raise DeserializationError(f"Generics are not supported for field '{field_name}'")

        if getter is None or length_function is None:
            raise DeserializationError(
                f"{fb_object.__class__.__name__} missing getter or Length method for field '{camel}'"
            )

        length = length_function()
        if length == 0:
            return []

        if issubclass(element_class, DataModel):
            return [element_class._deserialize_inner(getter(i)) for i in range(length)]

        if issubclass(element_class, (str, StrEnum)):
            return [cls._deserialize_string(getter(i), element_class) for i in range(length)]

        if element_class in (int, float, bool):
            raise DeserializationError("Primitive lists should be deserialized using _deserialize_numpy_array method")

        raise DeserializationError(f"Unsupported vector element type: {element_class} " f"for field '{field_name}'")

    def _serialize_numpy_array(self, builder: Builder, array: np.ndarray, field_name: str) -> int:
        if array.dtype != np.float32:
            raise SerializationError(
                f"Only np.float32 arrays are supported for serialization, got {array.dtype} for field '{field_name}'"
            )

        if array.ndim != 1:
            raise SerializationError(
                f"Only 1D numpy arrays are supported for serialization, got {array.ndim}D array for field '{field_name}'"
            )

        if np.isnan(array).any():
            raise SerializationError(
                f"Array contains NaN values, which are not supported for serialization for field '{field_name}'"
            )

        builder.StartVector(FLOAT32_SIZE, len(array), FLOAT32_SIZE)
        for value in reversed(array):
            builder.PrependFloat32(float(value))

        return builder.EndVector(len(array))

    @classmethod
    def _deserialize_numpy_array(cls, fb_object: Any, field_name: str) -> np.ndarray:
        camel = snake_to_camel(field_name)
        length_function = getattr(fb_object, f"{camel}Length")

        tab = fb_object._tab
        field_offset = tab.Offset(fb_object.__class__.__dict__[camel].__code__.co_consts[1])

        length = length_function()
        if length == 0 or field_offset == 0:
            return np.empty(0, dtype=np.float32)

        start = tab.Pos + field_offset
        buffer = memoryview(tab.Bytes)[start : start + length * FLOAT32_SIZE]
        array = np.frombuffer(buffer, dtype=np.float32)

        if np.isnan(array).any():
            raise DeserializationError(f"Deserialized array for '{field_name}' contains NaN values")

        return array

    @classmethod
    def _deserialize_from_table(cls, table: Table) -> Self:
        fb_class = cls.buffer_reader()
        wrapper = fb_class()
        wrapper.Init(table.Bytes, table.Pos)
        return cls._deserialize_inner(wrapper)

    @classmethod
    def _deserialize_union(cls, table: Table, field_values: SerializedData) -> Self:
        raise NotImplementedError("Subclasses must implement _deserialize_union method")

    @staticmethod
    def _prepend_offsets(builder: Builder, offsets: list[int]) -> int:
        builder.StartVector(FLOAT32_SIZE, len(offsets), FLOAT32_SIZE)
        for offset in reversed(offsets):
            builder.PrependUOffsetTRelative(offset)

        return builder.EndVector(len(offsets))
