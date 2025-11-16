from types import ModuleType
from typing import Self

import flatbuffers
import numpy as np
from pydantic import BaseModel

from sampletones.utils import snake_to_camel


class DataModel(BaseModel):
    @classmethod
    def buffer_reader(cls) -> type:
        raise NotImplementedError("Subclasses must implement buffer_reader method")

    @classmethod
    def buffer_builder(cls) -> ModuleType:
        raise NotImplementedError("Subclasses must implement buffer_builder method")

    def serialize(self) -> bytes:
        builder = flatbuffers.Builder(1024)
        offset = self._serialize_inner(builder)
        builder.Finish(offset)
        return bytes(builder.Output())

    @classmethod
    def deserialize(cls, buffer: bytes) -> "DataModel":
        fb_reader = cls.buffer_reader()
        root = fb_reader.GetRootAs(buffer, 0)
        return cls._deserialize_inner(root)

    def _serialize_inner(self, builder: flatbuffers.Builder) -> int:
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
                if len(value) == 0:
                    offsets[field_name] = 0
                elif all(isinstance(x, (int, float)) for x in value):
                    builder.StartVector(8, len(value), 8)
                    for x in reversed(value):
                        if isinstance(x, float):
                            builder.PrependFloat64(x)
                        else:
                            builder.PrependInt32(x)
                    offsets[field_name] = builder.EndVector(len(value))
                elif all(isinstance(model, DataModel) for model in value):
                    child_offsets = [model._serialize_inner(builder) for model in value]
                    builder.StartVector(4, len(child_offsets), 4)
                    for o in reversed(child_offsets):
                        builder.PrependUOffsetTRelative(o)
                    offsets[field_name] = builder.EndVector(len(child_offsets))
                else:
                    raise TypeError(f"Unsupported list element type for {field_name}")

            elif isinstance(value, str):
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
    def _deserialize_inner(cls, fb_obj) -> Self:
        field_values = {}

        for field_name, field_info in cls.model_fields.items():
            camel = snake_to_camel(field_name)
            getter = getattr(fb_obj, camel, None)
            if getter is None:
                raise AttributeError(f"{fb_obj.__class__.__name__} missing getter '{camel}'")

            annotation = field_info.annotation
            print(annotation)
            assert annotation is not None, f"Field '{field_name}' has no annotation"
            if annotation == np.ndarray:
                value = cls._deserialize_array(fb_obj, field_name)

            elif isinstance(annotation, type) and issubclass(annotation, DataModel):
                fb_child = getter()
                value = annotation._deserialize_inner(fb_child)

            else:
                value = getter()

            field_values[field_name] = value

        print(field_values)

        return cls(**field_values)

    def _serialize_array(self, builder: flatbuffers.Builder, array: np.ndarray) -> int:
        element_size = 4
        builder.StartVector(element_size, len(array), element_size)
        for x in reversed(array):
            builder.PrependFloat32(float(x))
        return builder.EndVector(len(array))

    @classmethod
    def _deserialize_array(cls, fb_obj, field_name: str) -> np.ndarray:
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
