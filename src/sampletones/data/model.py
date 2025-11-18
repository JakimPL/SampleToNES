from enum import StrEnum
from pathlib import Path
from types import ModuleType
from typing import Any, List, Self, Tuple, TypeVar, Union, get_args, get_origin

import numpy as np
from flatbuffers.builder import Builder
from flatbuffers.table import Table
from pydantic import BaseModel

from sampletones.typehints import SerializedData
from sampletones.utils import load_binary, save_binary, snake_to_camel

from .types import DataType


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
                offsets[field_name] = self._serialize_numpy_array(builder, value)

            elif isinstance(value, Path):
                offsets[field_name] = builder.CreateString(str(value))

            elif isinstance(value, list):
                offsets[field_name] = self._serialize_list(builder, value)

            elif isinstance(value, (str, StrEnum)):
                offsets[field_name] = builder.CreateString(value)

            elif isinstance(value, (int, float, bool)):
                offsets[field_name] = value

            else:
                raise TypeError(f"Unsupported field type {type(value)} for {field_name}")

        fb_builder.Start(builder)
        for field_name, val in offsets.items():
            camel = snake_to_camel(field_name)
            fb_add = getattr(fb_builder, f"Add{camel}")
            fb_add(builder, val)

        return fb_builder.End(builder)

    @classmethod
    def _deserialize_inner(cls, fb_obj: Any) -> Self:
        field_values: SerializedData = {}

        for field_name, field_info in cls.model_fields.items():
            camel = snake_to_camel(field_name)
            getter = getattr(fb_obj, camel, None)
            if getter is None:
                raise AttributeError(f"{fb_obj.__class__.__name__} missing getter '{camel}'")

            annotation = field_info.annotation
            assert annotation is not None, f"Field '{field_name}' has no annotation"

            if annotation is np.ndarray:
                value = cls._deserialize_numpy_array(fb_obj, field_name)

            elif annotation is Path:
                raw = getter().decode("utf-8")
                value = Path(raw)

            elif isinstance(annotation, TypeVar) or get_origin(annotation) is Union:
                table = getter()
                value = cls._deserialize_union(table, field_values)

            elif get_origin(annotation) is list:
                list_class = get_args(annotation)[0]
                value = cls._deserialize_list(fb_obj, field_name, list_class)

            elif issubclass(annotation, DataModel):
                fb_child = getter()
                value = annotation._deserialize_inner(fb_child)

            elif issubclass(annotation, (str, StrEnum)):
                string = getter().decode("utf-8")
                if issubclass(annotation, StrEnum):
                    value = annotation(string)
                else:
                    value = string

            else:
                value = getter()

            field_values[field_name] = value

        return cls(**field_values)

    def _serialize_list(self, builder: Builder, collection: list) -> int:
        if len(collection) == 0:
            return 0

        elif all(isinstance(value, (int, float)) for value in collection):
            builder.StartVector(8, len(collection), 8)
            for value in reversed(collection):
                if isinstance(value, float):
                    builder.PrependFloat64(value)
                else:
                    builder.PrependInt32(value)

            return builder.EndVector(len(collection))

        elif all(isinstance(value, (str, StrEnum)) for value in collection):
            string_offsets = []
            for value in collection:
                if isinstance(value, StrEnum):
                    value = value.value
                string_offsets.append(builder.CreateString(value))

            builder.StartVector(4, len(string_offsets), 4)
            for offset in reversed(string_offsets):
                builder.PrependUOffsetTRelative(offset)

            return builder.EndVector(len(string_offsets))

        elif all(isinstance(model, DataModel) for model in collection):
            child_offsets = [model._serialize_inner(builder) for model in collection]
            builder.StartVector(4, len(child_offsets), 4)
            for offset in reversed(child_offsets):
                builder.PrependUOffsetTRelative(offset)

            return builder.EndVector(len(child_offsets))

        elif all(isinstance(item, tuple) and len(item) == 2 for item in collection):
            entry_offsets: List[int] = []
            for first_element, second_element in collection:
                first_kind, first_payload = self._prepare_value_for_slot(builder, first_element)
                second_kind, second_payload = self._prepare_value_for_slot(builder, second_element)

                builder.StartObject(2)
                self._write_slot_to_builder(builder, 0, first_kind, first_payload)
                self._write_slot_to_builder(builder, 1, second_kind, second_payload)
                entry_offsets.append(builder.EndObject())

            builder.StartVector(4, len(entry_offsets), 4)
            for offset in reversed(entry_offsets):
                builder.PrependUOffsetTRelative(offset)

            return builder.EndVector(len(entry_offsets))

        raise TypeError(f"Unsupported list element type {type(collection[0])} or mixed types for serialization")

    @classmethod
    def _deserialize_list(cls, fb_obj: Any, field_name: str, element_class: type) -> np.ndarray | list:
        camel = snake_to_camel(field_name)
        getter = getattr(fb_obj, camel, None)
        length_function = getattr(fb_obj, f"{camel}Length", None)

        if getter is None or length_function is None:
            raise AttributeError(f"{fb_obj.__class__.__name__} missing getter or Length method for field '{camel}'")

        length = length_function()
        if length == 0:
            return []

        origin = get_origin(element_class)
        assert origin is None, f"Generics are not supported for field '{field_name}'"

        if issubclass(element_class, DataModel):
            items = []
            for i in range(length):
                items.append(element_class._deserialize_inner(getter(i)))
            return items

        if issubclass(element_class, (str, StrEnum)):
            items: List = []
            for i in range(length):
                raw = getter(i)
                string = raw.decode("utf-8")
                if issubclass(element_class, StrEnum):
                    string = element_class(string)
                items.append(string)
            return items

        if element_class in (int, float, bool):
            arr = []
            for i in range(length):
                arr.append(getter(i))
            return np.array(arr)

        raise TypeError(f"Unsupported vector element type: {element_class} " f"for field '{field_name}'")

    def _serialize_numpy_array(self, builder: Builder, array: np.ndarray) -> int:
        element_size = 4
        builder.StartVector(element_size, len(array), element_size)
        for value in reversed(array):
            builder.PrependFloat32(float(value))

        return builder.EndVector(len(array))

    @classmethod
    def _deserialize_numpy_array(cls, fb_obj: Any, field_name: str) -> np.ndarray:
        camel = snake_to_camel(field_name)
        length_function = getattr(fb_obj, f"{camel}Length")

        length = length_function()
        if length == 0:
            return np.empty(0, dtype=np.float32)

        tab = fb_obj._tab
        field_offset = tab.Offset(fb_obj.__class__.__dict__[camel].__code__.co_consts[1])

        if field_offset == 0:
            return np.empty(0, dtype=np.float32)

        start = tab.Pos + field_offset
        buffer = memoryview(tab.Bytes)[start : start + length * 4]

        return np.frombuffer(buffer, dtype=np.float32)

    @staticmethod
    def _prepare_value_for_slot(builder: Builder, value: Any) -> Tuple[DataType, object]:
        if isinstance(value, DataModel):
            return DataType.UOFFSET, value._serialize_inner(builder)
        if isinstance(value, str):
            return DataType.UOFFSET, builder.CreateString(value)
        if isinstance(value, float):
            return DataType.FLOAT64, float(value)
        if isinstance(value, int):
            return DataType.INT32, int(value)
        if isinstance(value, bool):
            return DataType.BOOL, bool(value)
        raise TypeError(f"Unsupported tuple element type {type(value)}")

    @staticmethod
    def _write_slot_to_builder(builder: Builder, slot_index: int, value_kind: DataType, value_payload: object) -> None:
        if value_kind == DataType.UOFFSET:
            return builder.PrependUOffsetTRelativeSlot(slot_index, value_payload, 0)
        if value_kind == DataType.FLOAT64:
            return builder.PrependFloat64Slot(slot_index, value_payload, 0.0)
        if value_kind == DataType.INT32:
            return builder.PrependInt32Slot(slot_index, value_payload, 0)
        if value_kind == DataType.BOOL:
            return builder.PrependBoolSlot(slot_index, value_payload, False)
        raise TypeError(f"Unsupported slot kind {value_kind}")

    @classmethod
    def _deserialize_from_table(cls, table: Table) -> Self:
        fb_class = cls.buffer_reader()
        wrapper = fb_class()
        wrapper.Init(table.Bytes, table.Pos)
        return cls._deserialize_inner(wrapper)

    @classmethod
    def _deserialize_union(cls, table: Table, field_values: SerializedData) -> Self:
        raise NotImplementedError("Subclasses must implement _deserialize_union method")
