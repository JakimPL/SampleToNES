from typing import Any, Protocol, runtime_checkable

from flatbuffers.builder import Builder


@runtime_checkable
class FlatBufferReaderProtocol(Protocol):
    @classmethod
    def GetRootAs(cls, buf: bytes, offset: int = 0) -> Any: ...  # pylint: disable=invalid-name

    def Init(self, buf: bytes, pos: int) -> None: ...  # pylint: disable=invalid-name


@runtime_checkable
class FlatBufferBuilderProtocol(Protocol):
    __name__: str

    def Start(self, builder: Builder) -> None: ...  # pylint: disable=invalid-name

    def End(self, builder: Builder) -> int: ...  # pylint: disable=invalid-name


@runtime_checkable
class FlatBufferUnionProtocol(Protocol):
    pass
