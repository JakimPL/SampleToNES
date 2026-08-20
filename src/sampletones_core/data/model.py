from __future__ import annotations

from abc import ABC
from enum import StrEnum
from pathlib import Path
from types import NoneType
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Self,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

import msgpack
import numpy as np
from pydantic import BaseModel

from sampletones_shared.array import to_numpy
from sampletones_shared.exceptions import (
    DeserializationError,
    SerializationError,
)
from sampletones_shared.types.array import (
    Array,
    ArrayClasses,
    NumericClasses,
)
from sampletones_shared.types.callback import Callback
from sampletones_shared.types.data import SerializedData
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import (
    load_binary,
    save_binary,
)


def _optional_inner_annotation(annotation: Any) -> Optional[Any]:
    """Returns the wrapped annotation of an ``Optional`` field, or ``None`` for a non-optional Union.

    ``Optional[X]`` is ``Union[X, None]``, so an optional field is a Union carrying ``NoneType`` among
    its arguments. Stripping ``NoneType`` yields the payload type to serialize when the value is set:
    a single remaining type is returned directly; several remaining types stay a Union so a tagged
    union still resolves through its ``union_map``.
    """
    if get_origin(annotation) is not Union:
        return None

    arguments = get_args(annotation)
    if NoneType not in arguments:
        return None

    payload = tuple(argument for argument in arguments if argument is not NoneType)
    if len(payload) == 1:
        return payload[0]

    return Union[payload]


class DataModel(BaseModel, ABC):
    def serialize(self) -> bytes:
        return bytes(msgpack.packb(self.serialize_inner(), use_bin_type=True))

    @classmethod
    def deserialize(
        cls,
        buffer: bytes,
        validation: Optional[Callback] = None,
        fast: bool = True,
    ) -> Self:
        data = msgpack.unpackb(buffer, raw=False)
        return cls.deserialize_inner(data, validation, fast=fast)

    def save(self, path: Pathlike) -> None:
        save_binary(path, self.serialize())

    @classmethod
    def load(cls, path: Pathlike, fast: bool = True) -> Self:
        return cls.deserialize(load_binary(path), fast=fast)

    @classmethod
    def _construct(cls, fast: bool = True, **data: Any) -> Self:
        if fast:
            return cls.model_construct(**data)

        return cls(**data)

    def serialize_inner(self) -> SerializedData:
        result: SerializedData = {}
        for field_name, field_info in self.__class__.model_fields.items():
            value = getattr(self, field_name)
            annotation = field_info.annotation
            result[field_name] = self._pack_value(value, annotation, field_name)

        return result

    @classmethod
    def deserialize_inner(
        cls,
        data: SerializedData,
        validation: Optional[Callback] = None,
        fast: bool = True,
    ) -> Self:
        field_values: SerializedData = {}
        for field_name, field_info in cls.model_fields.items():
            annotation = field_info.annotation
            raw = data.get(field_name)
            value = cls._unpack_value(
                raw,
                annotation,
                field_name,
                validation,
                fast,
            )
            if validation is not None:
                validation(value)

            field_values[field_name] = value

        return cls._construct(fast=fast, **field_values)

    def _pack_value(self, value: Any, annotation: Any, field_name: str) -> Any:
        if annotation is None:
            raise SerializationError(f"Field '{field_name}' has no annotation")

        if annotation in (Array, *ArrayClasses):
            return self._pack_array(value, field_name)

        if get_origin(annotation) is Union:
            optional_inner = _optional_inner_annotation(annotation)
            if optional_inner is not None:
                if value is None:
                    return None

                return self._pack_value(value, optional_inner, field_name)

            if isinstance(value, Path):
                return str(value)

            if isinstance(value, tuple):
                return [str(path) for path in value]

            return self._pack_union(value)

        if isinstance(annotation, TypeVar):
            return self._pack_union(value)

        if get_origin(annotation) is list:
            return self._pack_list(value, field_name)

        if issubclass(annotation, DataModel):
            return value.serialize_inner()

        if issubclass(annotation, (str, StrEnum)):
            return str(value)

        if annotation is Path:
            return str(value)

        if issubclass(annotation, (bool, *NumericClasses)):
            return value

        raise SerializationError(f"Unsupported field type {type(value)} for '{field_name}'")

    @classmethod
    def _unpack_value(
        cls,
        raw: Any,
        annotation: Any,
        field_name: str,
        validation: Optional[Callback] = None,
        fast: bool = True,
    ) -> Any:
        if annotation is None:
            raise DeserializationError(f"Field '{field_name}' has no annotation")

        if annotation in (Array, *ArrayClasses):
            return cls._unpack_array(raw, field_name)

        if get_origin(annotation) is Union:
            optional_inner = _optional_inner_annotation(annotation)
            if optional_inner is not None:
                if raw is None:
                    return None

                return cls._unpack_value(
                    raw,
                    optional_inner,
                    field_name,
                    validation,
                    fast,
                )

            if isinstance(raw, list):
                return tuple(Path(item) for item in raw)

            if isinstance(raw, str):
                return Path(raw)

            return cls._unpack_union(raw)

        if isinstance(annotation, TypeVar):
            return cls._unpack_union(raw)

        if get_origin(annotation) is list:
            list_class = get_args(annotation)[0]
            return cls._unpack_list(
                raw,
                field_name,
                list_class,
                validation,
                fast,
            )

        if issubclass(annotation, DataModel):
            return annotation.deserialize_inner(raw, validation, fast=fast)

        if issubclass(annotation, (str, StrEnum)):
            return cls._deserialize_string(raw, annotation)

        if annotation is Path:
            return Path(cls._deserialize_string(raw, str))

        if issubclass(annotation, (int, float, bool)):
            return annotation(raw)

        raise DeserializationError(f"Unsupported field type {annotation} for field '{field_name}'")

    def _pack_list(
        self,
        collection: List[Any],
        field_name: str,
    ) -> List[Any]:
        if not collection:
            return []

        if all(isinstance(value, (str, StrEnum)) for value in collection):
            return [str(value) for value in collection]

        if all(isinstance(model, DataModel) for model in collection):
            return [model.serialize_inner() for model in collection]

        if all(isinstance(value, (int, float, bool)) for value in collection):
            return list(collection)

        if all(isinstance(value, list) for value in collection):
            return [self._pack_list(value, field_name) for value in collection]

        raise SerializationError(
            f"Unsupported list element type {type(collection[0])} or mixed types for field '{field_name}'"
        )

    @classmethod
    def _unpack_list(
        cls,
        raw_list: Any,
        field_name: str,
        element_class: type,
        validation: Optional[Callback] = None,
        fast: bool = True,
    ) -> List[Any]:
        origin = get_origin(element_class)
        if origin is list:
            nested_element_class = get_args(element_class)[0]
            return [
                cls._unpack_list(
                    item,
                    field_name,
                    nested_element_class,
                    validation,
                    fast,
                )
                for item in raw_list
            ]

        if origin is not None:
            raise DeserializationError(f"Generics are not supported for field '{field_name}'")

        if not raw_list:
            return []

        if issubclass(element_class, DataModel):
            return [
                element_class.deserialize_inner(
                    item,
                    validation,
                    fast=fast,
                )
                for item in raw_list
            ]

        if issubclass(element_class, (str, StrEnum)):
            return [cls._deserialize_string(item, element_class) for item in raw_list]

        if issubclass(element_class, (int, float, bool)):
            return [element_class(item) for item in raw_list]

        raise DeserializationError(f"Unsupported vector element type: {element_class} for field '{field_name}'")

    def _pack_array(self, array: Array, field_name: str) -> bytes:
        array = to_numpy(array)

        if array.dtype != np.float32:
            raise SerializationError(
                f"Only np.float32 arrays are supported for serialization, "
                f"got {array.dtype} for field '{field_name}'"
            )

        if array.ndim != 1:
            raise SerializationError(
                f"Only 1D numpy arrays are supported for serialization, "
                f"got {array.ndim}D array for field '{field_name}'"
            )

        if np.isnan(array).any():
            raise SerializationError(
                f"Array contains NaN values, which are not supported for serialization for field '{field_name}'"
            )

        return array.tobytes()

    @classmethod
    def _unpack_array(cls, raw: bytes, field_name: str) -> np.ndarray:
        array = np.frombuffer(raw, dtype=np.float32).copy()

        if np.isnan(array).any():
            raise DeserializationError(f"Deserialized array for '{field_name}' contains NaN values")

        return array

    @classmethod
    def _deserialize_string(
        cls,
        raw: Union[str, bytes],
        string_class: Type[Union[str, bytes]],
    ) -> Union[str, StrEnum]:
        if isinstance(raw, bytes):
            try:
                string = raw.decode("utf-8")
            except UnicodeDecodeError as exception:
                raise DeserializationError("Failed to decode string from bytes") from exception
        else:
            string = raw

        if issubclass(string_class, StrEnum):
            return string_class(string)

        return string

    def _pack_union(self, value: Any) -> SerializedData:
        union_map: Optional[Dict[int, Type[DataModel]]] = self.__class__.union_map()
        if union_map is None:
            raise SerializationError(f"No union map defined for {self.__class__.__name__}")

        tag: Optional[int] = None
        for tag_type, member_cls in union_map.items():
            if isinstance(value, member_cls):
                tag = tag_type
                break

        if tag is None:
            raise SerializationError(f"No union tag for value {type(value).__name__} in {self.__class__.__name__}")

        return {"_type": tag, "_data": value.serialize_inner()}

    @classmethod
    def _unpack_union(cls, raw: SerializedData) -> Any:
        union_map = cls.union_map()
        if union_map is None:
            raise DeserializationError(f"No union map defined for {cls.__name__}")

        tag = raw["_type"]
        if tag == 0:
            raise DeserializationError(f"Union tag is 0 (null) for {cls.__name__}")

        target_cls: Optional[Type[DataModel]] = union_map.get(tag)
        if target_cls is None:
            raise DeserializationError(f"Unknown union tag {tag} for {cls.__name__}")

        return target_cls.deserialize_inner(raw["_data"])

    @classmethod
    def union_map(cls) -> Optional[Dict[int, Type[DataModel]]]:
        return None
