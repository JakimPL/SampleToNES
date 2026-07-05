import pytest
from pydantic import BaseModel, ValidationError

from sampletones_core.structures.collection.indexed import IndexedCollection
from tests.suite.dummy import ValueFrozenModel


class Holder(BaseModel):
    items: IndexedCollection[ValueFrozenModel]


def _holder(*values: int) -> Holder:
    return Holder(items=IndexedCollection(ValueFrozenModel(value=value) for value in values))


class TestIndexedCollectionSerialization:
    def test_dump_is_an_ordered_list(self) -> None:
        holder = _holder(3, 1, 2)
        assert holder.model_dump() == {"items": [{"value": 3}, {"value": 1}, {"value": 2}]}

    def test_round_trip_preserves_order_and_equality(self) -> None:
        holder = _holder(3, 1, 2)
        restored = Holder.model_validate(holder.model_dump())
        assert list(restored.items) == list(holder.items)
        assert restored.items == holder.items

    def test_json_round_trip(self) -> None:
        holder = _holder(5, 4)
        restored = Holder.model_validate_json(holder.model_dump_json())
        assert restored.model_dump() == holder.model_dump()

    def test_empty_collection(self) -> None:
        holder = Holder(items=IndexedCollection())
        assert holder.model_dump() == {"items": []}
        assert Holder.model_validate(holder.model_dump()).items == holder.items

    def test_existing_collection_passes_through(self) -> None:
        collection: IndexedCollection[ValueFrozenModel] = IndexedCollection([ValueFrozenModel(value=1)])
        holder = Holder(items=collection)
        assert isinstance(holder.items, IndexedCollection)

    def test_duplicate_items_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Holder.model_validate({"items": [{"value": 1}, {"value": 1}]})
