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

        for field_name, value in self.model_dump().items():
            camel = snake_to_camel(field_name)
            add_method = f"Add{camel}"

            fb_add = getattr(fb_builder, add_method, None)
            if fb_add is None:
                raise AttributeError(f"{fb_builder.__name__} missing '{add_method}' for field '{field_name}'")

            if isinstance(value, DataModel):
                offsets[field_name] = value._serialize_inner(builder)

            elif isinstance(value, np.ndarray):
                element_size = 8 if value.dtype == np.float64 else 4
                builder.StartVector(element_size, len(value), element_size)
                for x in reversed(value):
                    if value.dtype == np.float64:
                        builder.PrependFloat64(x)
                    elif value.dtype == np.float32:
                        builder.PrependFloat32(x)
                    elif np.issubdtype(value.dtype, np.integer):
                        builder.PrependInt32(int(x))
                    else:
                        raise TypeError(f"Unsupported ndarray dtype {value.dtype}")
                offsets[field_name] = builder.EndVector(len(value))

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

        for field_name in cls.model_fields.keys():
            print(field_name)
            camel = snake_to_camel(field_name)

            getter = getattr(fb_obj, camel, None)
            if getter is None:
                raise AttributeError(f"{fb_obj.__class__.__name__} missing getter '{camel}'")

            value = getter()
            field_values[field_name] = value

        return cls(**field_values)
