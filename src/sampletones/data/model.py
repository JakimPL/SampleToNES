from enum import StrEnum
from types import ModuleType
from typing import Any, List, Self, Tuple, TypeVar

import numpy as np
from flatbuffers.builder import Builder
from flatbuffers.table import Table
from pydantic import BaseModel

from sampletones.typehints import SerializedData
from sampletones.utils import snake_to_camel


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
                offsets[field_name] = self._serialize_array(builder, value)

            elif isinstance(value, list):
                offsets[field_name] = self._serialize_list(builder, value)

            elif isinstance(value, dict):
                offsets[field_name] = self._serialize_dict(builder, value)

            elif isinstance(value, (StrEnum, str)):
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
            print(field_name, field_info.annotation)
            camel = snake_to_camel(field_name)
            getter = getattr(fb_obj, camel, None)
            if getter is None:
                raise AttributeError(f"{fb_obj.__class__.__name__} missing getter '{camel}'")

            annotation = field_info.annotation
            assert annotation is not None, f"Field '{field_name}' has no annotation"

            if annotation == np.ndarray:
                value = cls._deserialize_array(fb_obj, field_name)

            elif annotation == list:
                value = cls._deserialize_list(fb_obj, field_name)

            elif annotation == dict:
                value = cls._deserialize_dict(fb_obj, field_name)

            elif isinstance(annotation, TypeVar):
                table = getter()
                value = cls.deserialize_union(table, field_values)

            elif issubclass(annotation, DataModel):
                fb_child = getter()
                value = annotation._deserialize_inner(fb_child)

            elif issubclass(annotation, StrEnum):
                string = getter().decode("utf-8")
                value = annotation(string)

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

                if first_kind == "uoffset":
                    builder.PrependUOffsetTRelativeSlot(0, first_payload, 0)
                elif first_kind == "float64":
                    builder.PrependFloat64Slot(0, first_payload, 0.0)
                elif first_kind == "int32":
                    builder.PrependInt32Slot(0, first_payload, 0)
                elif first_kind == "bool":
                    builder.PrependBoolSlot(0, first_payload, False)

                if second_kind == "uoffset":
                    builder.PrependUOffsetTRelativeSlot(1, second_payload, 0)
                elif second_kind == "float64":
                    builder.PrependFloat64Slot(1, second_payload, 0.0)
                elif second_kind == "int32":
                    builder.PrependInt32Slot(1, second_payload, 0)
                elif second_kind == "bool":
                    builder.PrependBoolSlot(1, second_payload, False)

                entry_offsets.append(builder.EndObject())

            builder.StartVector(4, len(entry_offsets), 4)
            for offset in reversed(entry_offsets):
                builder.PrependUOffsetTRelative(offset)

            return builder.EndVector(len(entry_offsets))

        raise TypeError(f"Unsupported list element type {type(collection[0])} or mixed types for serialization")

    @classmethod
    def _deserialize_list(cls, fb_obj: Any, field_name: str) -> list:
        return list(cls._deserialize_array(fb_obj, field_name))

    def _serialize_dict(self, builder: Builder, dictionary: dict) -> int:
        items = list(dictionary.items())
        return self._serialize_list(builder, items)

    @classmethod
    def _deserialize_dict(cls, fb_obj: Any, field_name: str) -> dict:
        keys = cls._deserialize_list(fb_obj, f"{field_name}_keys")
        values = cls._deserialize_list(fb_obj, f"{field_name}_values")
        return dict(zip(keys, values))

    def _serialize_array(self, builder: Builder, array: np.ndarray) -> int:
        element_size = 4
        builder.StartVector(element_size, len(array), element_size)
        for value in reversed(array):
            builder.PrependFloat32(float(value))

        return builder.EndVector(len(array))

    @classmethod
    def _deserialize_array(cls, fb_obj: Any, field_name: str) -> np.ndarray:
        camel = snake_to_camel(field_name)
        getter = getattr(fb_obj, camel, None)
        assert getter is not None, f"{fb_obj.__class__.__name__} missing getter '{camel}'"

        length_function = getattr(fb_obj, f"{camel}Length", None)
        if length_function is None or not callable(getter):
            raise AttributeError(f"{fb_obj.__class__.__name__} missing getter or Length for field '{field_name}'")

        length = length_function()
        assert isinstance(length, int)

        if length == 0:
            return np.empty(0)

        return np.array([getter(i) for i in range(length)])

    @staticmethod
    def _prepare_value_for_slot(builder: Builder, value: Any) -> Tuple[str, object]:
        if isinstance(value, DataModel):
            return "uoffset", value._serialize_inner(builder)
        if isinstance(value, str):
            return "uoffset", builder.CreateString(value)
        if isinstance(value, float):
            return "float64", float(value)
        if isinstance(value, int):
            return "int32", int(value)
        if isinstance(value, bool):
            return "bool", bool(value)
        raise TypeError(f"Unsupported tuple element type {type(value)}")

    @classmethod
    def _deserialize_from_table(cls, table: Table) -> Self:
        fb_cls = cls.buffer_reader()
        wrapper = fb_cls()
        wrapper.Init(table.Bytes, table.Pos)
        return cls._deserialize_inner(wrapper)

    @classmethod
    def deserialize_union(cls, table: Table, field_values: SerializedData) -> Self:
        raise NotImplementedError("Subclasses must implement _deserialize_union method")
