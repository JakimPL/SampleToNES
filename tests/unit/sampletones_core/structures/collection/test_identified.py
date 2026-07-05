import pytest
from pydantic import BaseModel, ValidationError

from sampletones_core.structures import IdentifiedCollection


class Item(BaseModel):
    id: str
    name: str

    def __hash__(self) -> int:
        return hash(self.id)


def _collection(*ids: str) -> IdentifiedCollection[Item]:
    return IdentifiedCollection(Item(id=identifier, name=identifier.upper()) for identifier in ids)


class TestIdentifiedCollection:
    def test_lookup_by_id(self) -> None:
        collection = _collection("aa", "bb", "cc")
        assert collection.get("bb").name == "BB"
        assert collection["cc"].name == "CC"
        assert collection.get("zz") is None

    def test_index_by_id(self) -> None:
        collection = _collection("aa", "bb", "cc")
        assert collection.get_index("aa") == 0
        assert collection.get_index("cc") == 2

    def test_id_is_the_key(self) -> None:
        item = Item(id="aa", name="A")
        assert IdentifiedCollection.hash(item) == "aa"

    def test_duplicate_id_rejected(self) -> None:
        collection = _collection("aa")
        with pytest.raises(ValueError):
            collection.append(Item(id="aa", name="other"))

    def test_reorder_preserves_id_resolution(self) -> None:
        collection = _collection("aa", "bb", "cc")
        collection.append(collection.pop(0))
        assert collection.get_index("aa") == 2
        assert collection.get("aa").name == "AA"


class Holder(BaseModel):
    items: IdentifiedCollection[Item]


class TestSerialization:
    def test_round_trip_rekeys_by_id(self) -> None:
        holder = Holder(items=_collection("aa", "bb"))
        restored = Holder.model_validate(holder.model_dump())
        assert restored.items.get("bb").name == "BB"
        assert restored.items.get_index("aa") == 0

    def test_json_round_trip(self) -> None:
        holder = Holder(items=_collection("aa", "bb"))
        restored = Holder.model_validate_json(holder.model_dump_json())
        assert restored.model_dump() == holder.model_dump()

    def test_duplicate_id_rejected_on_validate(self) -> None:
        with pytest.raises(ValidationError):
            Holder.model_validate({"items": [{"id": "aa", "name": "A"}, {"id": "aa", "name": "B"}]})
