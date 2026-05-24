from collections.abc import Hashable
from typing import TypeVar
from unittest.mock import patch

import numpy as np
import pytest

from sampletones_core.structures.collection.bidirectional import BidirectionalHashMap
from sampletones_core.structures.collection.indexed import IndexedCollection
from sampletones_shared.types.data import ModelHashable
from tests.sampletones.dummy import NonSerializableModel, SimpleModel, ValueFrozenModel, ValueObject

HashableT = TypeVar("HashableT", bound=ModelHashable)


class TestInitialization:
    def test_init_empty(self) -> None:
        collection = IndexedCollection[int]()
        assert len(collection) == 0
        assert bool(collection) is False
        assert list(collection) == []
        assert repr(collection) == "IndexedCollection([])"

    def test_init_with_integers(self) -> None:
        items = [1, 2, 3, 4, 5]
        collection = IndexedCollection[int](iter(items))
        assert len(collection) == 5
        assert list(collection) == items
        assert bool(collection) is True

    def test_init_with_strings(self) -> None:
        items = ["apple", "banana", "cherry"]
        collection = IndexedCollection[str](items)
        assert len(collection) == 3
        assert collection[0] == "apple"
        assert collection[2] == "cherry"

    def test_init_with_floats(self) -> None:
        items = [1.5, 2.7, 3.14159]
        collection = IndexedCollection[float](items)
        assert len(collection) == 3
        assert collection[1] == 2.7

    def test_init_with_bytes(self) -> None:
        items = [b"hello", b"world", b"test"]
        collection = IndexedCollection[bytes](items)
        assert len(collection) == 3
        assert collection[0] == b"hello"

    def test_init_with_bools(self) -> None:
        items = [True, False]
        collection = IndexedCollection[bool](items)
        assert len(collection) == 2
        assert collection[0] is True
        assert collection[1] is False

    def test_init_with_list_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            IndexedCollection([[1, 2], [3, 4]])

    def test_init_with_dict_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            IndexedCollection([{"a": 1}, {"b": 2}])

    def test_init_with_tuple_containing_immutable(self) -> None:
        IndexedCollection[tuple](((1, 2), (3, 4)))

    def test_init_with_tuple_containing_mutable_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            IndexedCollection(([], []))

    def test_init_with_duplicate_integers_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="already exists"):
            IndexedCollection[int]([1, 2, 1])

    def test_init_with_duplicate_strings_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="already exists"):
            IndexedCollection[str](["same", "different", "same"])

    def test_init_preserves_order(self) -> None:
        items = range(100)
        collection = IndexedCollection[int](items)
        assert list(collection) == list(items)

    def test_init_with_unhashable_models_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="unhashable"):
            IndexedCollection([SimpleModel(value=1, name="test")])

        with pytest.raises(TypeError, match="unhashable"):
            IndexedCollection([NonSerializableModel(data=np.array([]))])


class TestGetItem:
    def test_getitem_integers_by_positive_index(self) -> None:
        collection = IndexedCollection[int]([10, 20, 30])
        assert collection[0] == 10
        assert collection[1] == 20
        assert collection[2] == 30

    def test_getitem_strings_by_negative_index(self) -> None:
        collection = IndexedCollection[str](["a", "b", "c"])
        assert collection[-1] == "c"
        assert collection[-2] == "b"
        assert collection[-3] == "a"

    def test_getitem_floats_by_hash_string(self) -> None:
        value = 3.14159
        collection = IndexedCollection[float]([value])
        item_hash = IndexedCollection.hash(value)
        retrieved = collection[item_hash]
        assert retrieved == value

    def test_getitem_bytes_by_hash_after_multiple_insertions(self) -> None:
        items = [b"first", b"second", b"third", b"fourth"]
        collection = IndexedCollection[bytes](items)

        for item in items:
            item_hash = IndexedCollection.hash(item)
            assert collection[item_hash] == item

    def test_getitem_string_by_hash_only_no_index(self) -> None:
        collection = IndexedCollection[str](["alpha", "beta", "gamma"])

        hash_beta = IndexedCollection.hash("beta")
        assert collection[hash_beta] == "beta"

        hash_gamma = IndexedCollection.hash("gamma")
        assert collection[hash_gamma] == "gamma"

    def test_getitem_index_out_of_bounds_raises_index_error(self) -> None:
        collection = IndexedCollection[str](["only"])
        with pytest.raises(IndexError, match="out of bounds"):
            _ = collection[5]

    def test_getitem_negative_index_out_of_bounds_raises_index_error(self) -> None:
        collection = IndexedCollection[int]([42])
        with pytest.raises(IndexError, match="out of bounds"):
            _ = collection[-2]

    def test_getitem_nonexistent_hash_raises_key_error(self) -> None:
        collection = IndexedCollection[bool]([True])
        with pytest.raises(KeyError, match="not found"):
            _ = collection["nonexistent_hash"]

    def test_getitem_wrong_type_raises_type_error(self) -> None:
        collection = IndexedCollection[str](["test"])
        with pytest.raises(TypeError, match="must be a position"):
            _ = collection[3.14]

    def test_getitem_from_empty_raises_index_error(self) -> None:
        collection = IndexedCollection[int]()
        with pytest.raises(IndexError):
            _ = collection[0]

    def test_getitem_slice_returns_new_collection(self) -> None:
        collection = IndexedCollection[int]([1, 2, 3, 4, 5])
        result = collection[1:4]
        assert isinstance(result, IndexedCollection)
        assert list(result) == [2, 3, 4]

    def test_getitem_slice_with_step(self) -> None:
        collection = IndexedCollection[str](["a", "b", "c", "d", "e"])
        result = collection[::2]
        assert list(result) == ["a", "c", "e"]

    def test_getitem_slice_negative_indices(self) -> None:
        collection = IndexedCollection[float]([1.1, 2.2, 3.3, 4.4])
        result = collection[-3:-1]
        assert list(result) == [2.2, 3.3]


class TestSetItem:
    def test_setitem_strings_by_index_replaces_item(self) -> None:
        collection = IndexedCollection[str](["old", "keep"])
        collection[0] = "new"
        assert collection[0] == "new"
        assert len(collection) == 2
        assert collection[1] == "keep"

    def test_setitem_integers_by_negative_index(self) -> None:
        collection = IndexedCollection[int]([100, 200])
        collection[-1] = 300
        assert collection[-1] == 300
        assert collection[0] == 100

    def test_setitem_floats_by_hash_replaces_item(self) -> None:
        collection = IndexedCollection[float]([1.1, 2.2])
        old_hash = IndexedCollection.hash(1.1)
        collection[old_hash] = 3.3
        assert collection[0] == 3.3

        with pytest.raises(KeyError):
            _ = collection[old_hash]

    def test_setitem_bytes_same_item_at_same_position_no_op(self) -> None:
        item = b"same"
        other = b"different"
        collection = IndexedCollection[bytes]([item, other])
        collection[0] = item
        assert collection[0] == item
        assert len(collection) == 2

    def test_setitem_bools_equivalent_item_at_same_position_no_op(self) -> None:
        collection = IndexedCollection[bool]([True, False])
        collection[0] = True
        assert len(collection) == 2
        assert collection[0] is True

    def test_setitem_integers_item_exists_elsewhere_raises_value_error(self) -> None:
        collection = IndexedCollection[int]([1, 2, 3])
        with pytest.raises(ValueError, match="already exists"):
            collection[0] = 2

    def test_setitem_strings_preserves_other_items_indices(self) -> None:
        items = ["a", "b", "c", "d", "e"]
        collection = IndexedCollection[str](items)
        collection[2] = "new"

        assert collection[0] == "a"
        assert collection[1] == "b"
        assert collection[2] == "new"
        assert collection[3] == "d"
        assert collection[4] == "e"

    def test_setitem_floats_updates_hash_mapping(self) -> None:
        collection = IndexedCollection[float]([1.1, 2.2])
        old_hash = IndexedCollection.hash(1.1)
        new_hash = IndexedCollection.hash(3.3)

        collection[0] = 3.3

        assert collection[new_hash] == 3.3
        with pytest.raises(KeyError):
            _ = collection[old_hash]

    def test_setitem_using_hash_of_present_item(self) -> None:
        items = ["a", "b", "c"]
        collection = IndexedCollection[str](items)

        hash_b = IndexedCollection.hash("b")
        original_position_of_b = collection.get_index(hash_b)

        collection[hash_b] = "new_b"

        assert collection[original_position_of_b] == "new_b"
        assert collection.get_index(IndexedCollection.hash("new_b")) == original_position_of_b
        with pytest.raises(KeyError):
            _ = collection[hash_b]

    def test_setitem_using_hash_of_removed_item(self) -> None:
        collection = IndexedCollection[int]([1, 2, 3])

        hash_2 = IndexedCollection.hash(2)
        del collection[1]

        with pytest.raises(KeyError):
            collection[hash_2] = 99

    def test_setitem_by_hash_replaces_at_correct_position(self) -> None:
        collection = IndexedCollection[str](["first", "second", "third"])

        hash_second = IndexedCollection.hash("second")
        collection[hash_second] = "SECOND"

        assert collection[0] == "first"
        assert collection[1] == "SECOND"
        assert collection[2] == "third"
        assert len(collection) == 3

    def test_setitem_out_of_bounds_raises_index_error(self) -> None:
        collection = IndexedCollection[int]([1])
        with pytest.raises(IndexError):
            collection[10] = 2

    def test_setitem_with_hash_collision(self) -> None:
        collection = IndexedCollection[str](["item1", "item2"])
        item1_hash = IndexedCollection.hash("item1")
        item2_hash = IndexedCollection.hash("item2")

        with patch(
            "sampletones_core.structures.collection.indexed.IndexedCollection.hash",
            return_value=item1_hash,
        ):
            with pytest.raises(ValueError, match="already exists"):
                collection[item2_hash] = "item2"  # should raise since "item2" has now the same hash as "item1"

            collection[item1_hash] = "item1"  # no change, should work fine
            collection[item1_hash] = "item2"  # should work since "item_hash -> item2" is seen by the collection
            assert all(item == "item2" for item in collection)


class TestDelItem:
    def test_delitem_integers_by_positive_index(self) -> None:
        collection = IndexedCollection[int]([10, 20, 30])
        del collection[1]
        assert len(collection) == 2
        assert collection[0] == 10
        assert collection[1] == 30

    def test_delitem_strings_by_negative_index(self) -> None:
        collection = IndexedCollection[str](["a", "b", "c"])
        del collection[-1]
        assert len(collection) == 2
        assert list(collection) == ["a", "b"]

    def test_delitem_floats_by_hash(self) -> None:
        items = [1.1, 2.2, 3.3]
        collection = IndexedCollection[float](items)
        item_hash = IndexedCollection.hash(2.2)
        del collection[item_hash]
        assert len(collection) == 2
        assert collection[0] == 1.1
        assert collection[1] == 3.3

    def test_delitem_bytes_reindexes_subsequent_items(self) -> None:
        items = [b"a", b"b", b"c", b"d", b"e"]
        collection = IndexedCollection[bytes](items)
        del collection[1]

        assert collection[0] == b"a"
        assert collection[1] == b"c"
        assert collection[2] == b"d"
        assert collection[3] == b"e"

    def test_delitem_bools_removes_hash_mapping(self) -> None:
        collection = IndexedCollection[bool]([True, False])
        item_hash = IndexedCollection.hash(True)
        del collection[0]

        with pytest.raises(KeyError):
            _ = collection[item_hash]

    def test_delitem_by_hash_middle_element(self) -> None:
        items = [10, 20, 30, 40, 50]
        collection = IndexedCollection[int](items)

        hash_30 = IndexedCollection.hash(30)
        del collection[hash_30]

        assert len(collection) == 4
        assert 30 not in collection
        assert collection[2] == 40

    def test_delitem_by_hash_first_element(self) -> None:
        collection = IndexedCollection[str](["remove", "keep1", "keep2"])

        hash_remove = IndexedCollection.hash("remove")
        del collection[hash_remove]

        assert collection[0] == "keep1"
        assert collection[1] == "keep2"

    def test_delitem_strings_first_and_last(self) -> None:
        collection = IndexedCollection[str](["first", "middle", "last"])
        del collection[0]
        del collection[-1]
        assert len(collection) == 1
        assert collection[0] == "middle"

    def test_delitem_out_of_bounds_raises_index_error(self) -> None:
        collection = IndexedCollection[int]([42])
        with pytest.raises(IndexError):
            del collection[10]

    def test_delitem_nonexistent_hash_raises_key_error(self) -> None:
        collection = IndexedCollection[str](["test"])
        with pytest.raises(KeyError):
            del collection["nonexistent"]


class TestContains:
    def test_contains_existing_integer(self) -> None:
        collection = IndexedCollection[int]([1, 2, 3])
        assert 2 in collection

    def test_contains_existing_string(self) -> None:
        collection = IndexedCollection[str](["hello", "world"])
        assert "hello" in collection

    def test_contains_nonexistent_float(self) -> None:
        collection = IndexedCollection[float]([1.1, 2.2])
        assert 3.3 not in collection

    def test_contains_bytes_after_removal(self) -> None:
        item = b"remove_me"
        collection = IndexedCollection[bytes]([item, b"keep"])
        del collection[0]
        assert item not in collection

    def test_contains_with_hash_collision_different_items_same_hash(self) -> None:
        item1 = "first"
        collection = IndexedCollection[str]([item1])

        with patch(
            "sampletones_core.structures.collection.indexed.IndexedCollection.hash",
            return_value=IndexedCollection.hash(item1),
        ):
            item2 = "second"
            assert item2 in collection

    def test_contains_checks_hash_not_equality(self) -> None:
        collection = IndexedCollection[int]([42])

        with patch(
            "sampletones_core.structures.collection.indexed.IndexedCollection.hash",
            return_value="fake_hash",
        ):
            assert 42 not in collection

    def test_contains_false_vs_zero_int(self) -> None:
        # Depends on hash implementation whether these collide or not
        hash_false = IndexedCollection.hash(False)
        hash_zero = IndexedCollection.hash(0)

        collection_with_false = IndexedCollection[bool]([False])
        collection_with_zero = IndexedCollection[int]([0])

        assert False in collection_with_false
        assert 0 in collection_with_zero

        if hash_false == hash_zero:
            assert 0 in collection_with_false
            assert False in collection_with_zero
        else:
            assert 0 not in collection_with_false
            assert False not in collection_with_zero

    def test_contains_zero_int_vs_zero_float(self) -> None:
        # Depends on hash implementation whether these collide or not
        hash_int_zero = IndexedCollection.hash(0)
        hash_float_zero = IndexedCollection.hash(0.0)

        collection_with_int = IndexedCollection[int]([0])
        collection_with_float = IndexedCollection[float]([0.0])

        assert 0 in collection_with_int
        assert 0.0 in collection_with_float

        if hash_int_zero == hash_float_zero:
            assert 0.0 in collection_with_int
            assert 0 in collection_with_float
        else:
            assert 0.0 not in collection_with_int
            assert 0 not in collection_with_float

    def test_contains_false_vs_zero_float(self) -> None:
        # Depends on hash implementation whether these collide or not
        hash_false = IndexedCollection.hash(False)
        hash_float_zero = IndexedCollection.hash(0.0)

        collection_with_false = IndexedCollection[bool]([False])
        collection_with_float = IndexedCollection[float]([0.0])

        assert False in collection_with_false
        assert 0.0 in collection_with_float

        if hash_false == hash_float_zero:
            assert 0.0 in collection_with_false
            assert False in collection_with_float
        else:
            assert 0.0 not in collection_with_false
            assert False not in collection_with_float

    def test_contains_zero_vs_zero_byte(self) -> None:
        collection_with_int = IndexedCollection[int]([0])
        collection_with_bytes = IndexedCollection[bytes]([b"\x00"])

        assert 0 in collection_with_int
        assert b"\x00" not in collection_with_int

        assert b"\x00" in collection_with_bytes
        assert 0 not in collection_with_bytes

    def test_contains_false_vs_zero_byte(self) -> None:
        collection_with_false = IndexedCollection[bool]([False])
        collection_with_bytes = IndexedCollection[bytes]([b"\x00"])

        assert False in collection_with_false
        assert b"\x00" not in collection_with_false

        assert b"\x00" in collection_with_bytes
        assert False not in collection_with_bytes


class TestEq:
    def test_eq_empty_collections(self) -> None:
        collection1 = IndexedCollection[int]()
        collection2 = IndexedCollection[int]()
        assert collection1 == collection2
        assert collection1 is not collection2

    def test_eq_same_integers_same_order(self) -> None:
        collection1 = IndexedCollection[int]([1, 2, 3])
        collection2 = IndexedCollection[int]([1, 2, 3])
        assert collection1 == collection2
        assert collection1 is not collection2

    def test_eq_same_strings_different_order(self) -> None:
        collection1 = IndexedCollection[str](["a", "b", "c"])
        collection2 = IndexedCollection[str](["c", "b", "a"])
        assert collection1 != collection2
        assert collection1 is not collection2

    def test_eq_different_lengths(self) -> None:
        collection1 = IndexedCollection[int]([1, 2])
        collection2 = IndexedCollection[int]([1, 2, 3])
        assert collection1 != collection2
        assert collection1 is not collection2

    def test_eq_different_items_same_length(self) -> None:
        collection1 = IndexedCollection[int]([1, 2, 3])
        collection2 = IndexedCollection[int]([4, 5, 6])
        assert collection1 != collection2

    def test_eq_with_non_indexed_collection(self) -> None:
        collection = IndexedCollection[int]([1, 2, 3])
        assert collection != [1, 2, 3]
        assert collection != {1, 2, 3}
        assert collection != "123"
        assert collection != None
        assert collection != 123

    def test_eq_same(self) -> None:
        collection = IndexedCollection[float]([1.1, 2.2, 3.3])
        assert collection == collection

    def test_eq_copied_collection(self) -> None:
        original = IndexedCollection[str](["a", "b", "c"])
        copy = original.copy()
        assert original == copy
        assert original is not copy

    def test_eq_after_modifications_no_longer_equal(self) -> None:
        collection1 = IndexedCollection[int]([1, 2, 3])
        collection2 = IndexedCollection[int]([1, 2, 3])
        assert collection1 == collection2

        collection1.append(4)
        assert collection1 != collection2

    def test_eq_same_hashes_different_items(self) -> None:
        collection1 = IndexedCollection[int]([10, 20])

        hash1_10 = IndexedCollection.hash(10)
        hash1_20 = IndexedCollection.hash(20)

        with patch(
            "sampletones_core.structures.collection.indexed.IndexedCollection.hash",
            side_effect=[hash1_10, hash1_20],
        ):
            collection2 = IndexedCollection[int]([30, 40])
            assert collection1 == collection2

    def test_eq_different_items_equal_by_value(self) -> None:
        item1_a = ValueObject(value=1)
        item1_b = ValueObject(value=2)

        item2_a = ValueObject(value=1)
        item2_b = ValueObject(value=2)
        collection1 = IndexedCollection[ValueObject]([item1_a, item1_b])
        collection2 = IndexedCollection[ValueObject]([item2_a, item2_b])

        assert collection1 == collection2

    def test_eq_equal_items_different_hashes(self) -> None:
        with patch("sampletones_core.structures.collection.indexed.IndexedCollection.hash") as mock:
            mock.side_effect = ["hash_a", "hash_b"]
            collection1 = IndexedCollection[int]([1, 2])

            mock.side_effect = ["hash_c", "hash_d"]
            collection2 = IndexedCollection[int]([1, 2])

            assert collection1 != collection2

    def test_eq_vile_example_same_items_swapped_hashes(self) -> None:
        with patch("sampletones_core.structures.collection.indexed.IndexedCollection.hash") as mock:
            mock.side_effect = ["0", "1"]
            collection1 = IndexedCollection[int]([0, 1])

            mock.side_effect = ["1", "0"]
            collection2 = IndexedCollection[int]([0, 1])

            assert collection1 != collection2
            assert list(collection1) == [0, 1]
            assert list(collection2) == [0, 1]
            assert collection1.get_hash(0) == "0"
            assert collection1.get_hash(1) == "1"
            assert collection2.get_hash(0) == "1"
            assert collection2.get_hash(1) == "0"

    def test_eq_vile_example_reversed_items_swapped_hashes(self) -> None:
        with patch("sampletones_core.structures.collection.indexed.IndexedCollection.hash") as mock:
            mock.side_effect = ["0", "1"]
            collection1 = IndexedCollection[int]([0, 1])

            mock.side_effect = ["0", "1"]
            collection2 = IndexedCollection[int]([1, 0])

            assert collection1 == collection2
            assert list(collection1) != list(collection2)

    def test_eq_symmetry(self) -> None:
        collection1 = IndexedCollection[int]([1, 2, 3])
        collection2 = IndexedCollection[int]([1, 2, 3])

        assert collection1 == collection2
        assert collection2 == collection1

    def test_eq_reflexivity(self) -> None:
        collection1 = IndexedCollection[int]([1, 2, 3])
        collection2 = collection1
        assert collection1 == collection2
        assert collection1 is collection2

    def test_eq_transitivity(self) -> None:
        common_order = BidirectionalHashMap[int](
            {
                "hash_a": 0,
                "hash_b": 1,
                "hash_c": 2,
            }
        )
        collection1 = IndexedCollection[str]()
        collection1._items = {"hash_a": "item1", "hash_b": "item2", "hash_c": "item3"}
        collection1._order = common_order

        collection2 = IndexedCollection[str]()
        collection2._items = {"hash_b": "different2", "hash_c": "different3", "hash_a": "different1"}
        collection2._order = common_order.copy()

        collection3 = IndexedCollection[str]()
        collection3._items = {"hash_c": "other3", "hash_b": "other2", "hash_a": "other1"}
        collection3._order = BidirectionalHashMap(
            {key: value for key, value in reversed(list(common_order.items_forward()))}
        )

        assert collection1 == collection2
        assert collection2 == collection3
        assert collection1 == collection3


class TestIter:
    def test_iter_empty_collection(self) -> None:
        collection = IndexedCollection[str]()
        assert list(collection) == []

    def test_iter_integers_preserves_insertion_order(self) -> None:
        items = list(range(10))
        collection = IndexedCollection[int](items)
        assert list(collection) == items

    def test_iter_strings_after_deletions(self) -> None:
        items = ["a", "b", "c", "d", "e"]
        collection = IndexedCollection[str](items)
        del collection[1]
        del collection[2]
        expected = ["a", "c", "e"]
        assert list(collection) == expected

    def test_iter_floats_after_insertions(self) -> None:
        collection = IndexedCollection[float]([1.1, 3.3])
        collection.insert(1, 2.2)
        result = list(collection)
        assert result == [1.1, 2.2, 3.3]


class TestLen:
    def test_len_empty(self) -> None:
        collection = IndexedCollection[bytes]()
        assert len(collection) == 0

    def test_len_integers_after_append(self) -> None:
        collection = IndexedCollection[int]()
        collection.append(1)
        assert len(collection) == 1
        collection.append(2)
        assert len(collection) == 2

    def test_len_strings_after_pop(self) -> None:
        collection = IndexedCollection[str](["a", "b", "c", "d", "e"])
        collection.pop()
        assert len(collection) == 4

    def test_len_floats_after_clear(self) -> None:
        collection = IndexedCollection[float]([1.1, 2.2, 3.3])
        collection.clear()
        assert len(collection) == 0


class TestBool:
    def test_bool_empty_is_false(self) -> None:
        collection = IndexedCollection[int]()
        assert not collection

    def test_bool_nonempty_is_true(self) -> None:
        collection = IndexedCollection[str](["something"])
        assert collection

    def test_bool_after_clear_is_false(self) -> None:
        collection = IndexedCollection[bool]([True, False])
        assert collection
        collection.clear()
        assert not collection


class TestRepr:
    def test_repr_empty(self) -> None:
        collection = IndexedCollection[int]()
        assert repr(collection) == "IndexedCollection([])"

    def test_repr_with_integers(self) -> None:
        collection = IndexedCollection[int]([1, 2, 3])
        assert repr(collection) == "IndexedCollection([1, 2, 3])"

    def test_repr_with_strings(self) -> None:
        collection = IndexedCollection[str](["test"])
        assert repr(collection) == "IndexedCollection(['test'])"

    def test_repr_with_models(self) -> None:
        first_object = ValueFrozenModel(value=42)
        collection = IndexedCollection[ValueFrozenModel]([first_object])
        first_representation = f"IndexedCollection([{repr(first_object)}])"
        second_representation = (
            f"IndexedCollection([{repr(ValueFrozenModel(value=42))}])"  # should not depend on identity
        )
        assert repr(collection) == first_representation
        assert repr(collection) == second_representation


class TestGet:
    def test_get_integer_by_index_existing(self) -> None:
        collection = IndexedCollection[int]([42])
        assert collection.get(0) == 42

    def test_get_string_by_negative_index_existing(self) -> None:
        collection = IndexedCollection[str](["a", "b"])
        assert collection.get(-1) == "b"

    def test_get_float_by_hash_existing(self) -> None:
        value = 3.14
        collection = IndexedCollection[float]([value])
        item_hash = IndexedCollection.hash(value)
        assert collection.get(item_hash) == value

    def test_get_by_hash_multiple_items(self) -> None:
        items = ["alpha", "beta", "gamma", "delta"]
        collection = IndexedCollection[str](items)

        for item in items:
            item_hash = IndexedCollection.hash(item)
            assert collection.get(item_hash) == item

    def test_get_by_hash_returns_none_for_nonexistent(self) -> None:
        collection = IndexedCollection[int]([1, 2, 3])
        fake_hash = "nonexistent_hash"
        assert collection.get(fake_hash) is None

    def test_get_by_hash_with_custom_default(self) -> None:
        collection = IndexedCollection[str](["exists"])
        default = "default_value"
        assert collection.get("fake_hash", default) == default

    def test_get_index_out_of_bounds_returns_default(self) -> None:
        collection = IndexedCollection[int]([1])
        assert collection.get(10) is None

    def test_get_nonexistent_hash_returns_default(self) -> None:
        collection = IndexedCollection[str](["test"])
        assert collection.get("nonexistent") is None

    def test_get_with_custom_default(self) -> None:
        collection = IndexedCollection[int]()
        assert collection.get(0, 999) == 999

    def test_get_wrong_type_raises_type_error(self) -> None:
        collection = IndexedCollection[str](["a"])
        with pytest.raises(TypeError):
            collection.get(3.14)


class TestClear:
    def test_clear_empty_collection(self) -> None:
        collection = IndexedCollection[int]()
        collection.clear()
        assert len(collection) == 0

    def test_clear_integers_populated_collection(self) -> None:
        collection = IndexedCollection[int]([1, 2, 3, 4, 5])
        collection.clear()
        assert len(collection) == 0
        assert list(collection) == []

    def test_clear_strings_removes_all_hashes(self) -> None:
        items = ["a", "b"]
        collection = IndexedCollection[str](items)
        hashes = [IndexedCollection.hash(item) for item in items]

        collection.clear()

        for hash in hashes:
            with pytest.raises(KeyError):
                _ = collection[hash]

    def test_operations_after_clear(self) -> None:
        collection = IndexedCollection[float]([1.1])
        collection.clear()
        collection.append(2.2)
        assert collection[0] == 2.2


class TestCopy:
    def test_copy_empty_collection(self) -> None:
        collection = IndexedCollection[int]()
        copy = collection.copy()
        assert collection == copy
        assert len(copy) == 0
        assert list(copy) == []

    def test_copy_strings_populated_collection(self) -> None:
        items = ["a", "b", "c"]
        collection = IndexedCollection[str](items)
        copy = collection.copy()
        assert collection == copy
        assert list(copy) == items
        assert len(copy) == len(collection)

    def test_copy_integers_is_independent(self) -> None:
        collection = IndexedCollection[int]([1, 2])
        copy = collection.copy()
        assert collection == copy

        collection.append(3)
        assert len(collection) == 3
        assert len(copy) == 2

    def test_copy_models_is_shallow(self) -> None:
        items = [ValueObject(value=1)]
        collection = IndexedCollection[ValueObject](items)
        copy = collection.copy()
        assert copy[0] is items[0]

    def test_copy_immutable_strings_shallow_but_same_values(self) -> None:
        items = ["immutable1", "immutable2", "immutable3"]
        collection = IndexedCollection[str](items)
        copy = collection.copy()

        assert collection == copy
        assert list(copy) == items
        for i in range(len(items)):
            assert copy[i] == collection[i]

    def test_copy_integers_independent_modifications(self) -> None:
        collection = IndexedCollection[int]([1, 2, 3])
        copy = collection.copy()

        collection[0] = 999
        del collection[1]

        assert 999 in collection
        assert copy[0] == 1
        assert copy[1] == 2
        assert copy[2] == 3
        assert len(copy) == 3

    def test_copy_preserves_hash_access(self) -> None:
        items = ["a", "b", "c"]
        collection = IndexedCollection[str](items)
        copy = collection.copy()

        for item in items:
            item_hash = IndexedCollection.hash(item)
            assert copy[item_hash] == item


class TestAppend:
    def test_append_integer_to_empty(self) -> None:
        collection = IndexedCollection[int]()
        collection.append(42)
        assert len(collection) == 1
        assert collection[0] == 42

    def test_append_multiple_strings(self) -> None:
        collection = IndexedCollection[str]()
        items = ["a", "b", "c", "d", "e"]
        for item in items:
            collection.append(item)
        assert list(collection) == items

    def test_append_duplicate_float_raises_value_error(self) -> None:
        collection = IndexedCollection[float]([1.5])
        with pytest.raises(ValueError, match="already exists"):
            collection.append(1.5)

    def test_append_bytes_updates_indices(self) -> None:
        collection = IndexedCollection[bytes]([b"a"])
        items = [b"b", b"c", b"d"]
        for item in items:
            collection.append(item)

        assert len(collection) == 4
        assert collection[0] == b"a"
        for i, item in enumerate(items):
            assert collection[i + 1] == item


class TestExtend:
    def test_extend_integers_empty_collection(self) -> None:
        collection = IndexedCollection[int]()
        items = [1, 2, 3]
        collection.extend(items)
        assert list(collection) == items

    def test_extend_strings_populated_collection(self) -> None:
        collection = IndexedCollection[str](["initial"])
        new_items = ["added1", "added2"]
        collection.extend(new_items)
        assert len(collection) == 3
        assert list(collection) == ["initial", "added1", "added2"]

    def test_extend_with_empty_iterator(self) -> None:
        collection = IndexedCollection[float]([1.1])
        collection.extend([])
        assert len(collection) == 1

    def test_extend_bytes_with_duplicate_raises_value_error(self) -> None:
        item = b"duplicate"
        collection = IndexedCollection[bytes]([item])
        with pytest.raises(ValueError, match="already exists"):
            collection.extend([b"new", item])


class TestInsert:
    def test_insert_integer_at_beginning(self) -> None:
        collection = IndexedCollection[int]([2, 3])
        collection.insert(0, 1)
        assert collection[0] == 1
        assert collection[1] == 2
        assert collection[2] == 3

    def test_insert_string_at_middle(self) -> None:
        collection = IndexedCollection[str](["a", "c"])
        collection.insert(1, "b")
        assert collection[0] == "a"
        assert collection[1] == "b"
        assert collection[2] == "c"

    def test_insert_float_at_end(self) -> None:
        collection = IndexedCollection[float]([1.1, 2.2])
        collection.insert(2, 3.3)
        assert collection[2] == 3.3

    def test_insert_bytes_into_empty(self) -> None:
        collection = IndexedCollection[bytes]()
        collection.insert(0, b"first")
        assert collection[0] == b"first"

    def test_insert_integers_updates_all_subsequent_indices(self) -> None:
        items = list(range(5))
        collection = IndexedCollection[int](items)
        collection.insert(2, 99)

        assert collection[0] == 0
        assert collection[1] == 1
        assert collection[2] == 99
        assert collection[3] == 2
        assert collection[4] == 3
        assert collection[5] == 4

    def test_insert_duplicate_string_raises_value_error(self) -> None:
        collection = IndexedCollection[str](["exists"])
        with pytest.raises(ValueError, match="already exists"):
            collection.insert(0, "exists")

    def test_insert_negative_index_raises_index_error(self) -> None:
        collection = IndexedCollection[int]()
        with pytest.raises(IndexError):
            collection.insert(-1, 1)

    def test_insert_out_of_bounds_raises_index_error(self) -> None:
        collection = IndexedCollection[str](["only"])
        with pytest.raises(IndexError):
            collection.insert(10, "too far")


class TestPop:
    def test_pop_integer_default_removes_last(self) -> None:
        collection = IndexedCollection[int]([1, 2, 3])
        popped = collection.pop()
        assert popped == 3
        assert len(collection) == 2

    def test_pop_string_by_positive_index(self) -> None:
        collection = IndexedCollection[str](["a", "b", "c"])
        popped = collection.pop(1)
        assert popped == "b"
        assert len(collection) == 2
        assert collection[0] == "a"
        assert collection[1] == "c"

    def test_pop_float_by_negative_index(self) -> None:
        collection = IndexedCollection[float]([1.1, 2.2, 3.3])
        popped = collection.pop(-2)
        assert popped == 2.2

    def test_pop_bytes_by_hash(self) -> None:
        items = [b"first", b"second"]
        collection = IndexedCollection[bytes](items)
        item_hash = IndexedCollection.hash(b"first")
        popped = collection.pop(item_hash)
        assert popped == b"first"
        assert len(collection) == 1

    def test_pop_from_empty_raises_index_error(self) -> None:
        collection = IndexedCollection[int]()
        with pytest.raises(IndexError, match="empty"):
            collection.pop()

    def test_pop_out_of_bounds_raises_index_error(self) -> None:
        collection = IndexedCollection[str](["only"])
        with pytest.raises(IndexError):
            collection.pop(10)

    def test_pop_nonexistent_hash_raises_key_error(self) -> None:
        collection = IndexedCollection[float]([1.1])
        with pytest.raises(KeyError):
            collection.pop("nonexistent")


class TestRemove:
    def test_remove_existing_integer(self) -> None:
        collection = IndexedCollection[int]([10, 20, 30])
        collection.remove(20)
        assert len(collection) == 2
        assert collection[0] == 10
        assert collection[1] == 30

    def test_remove_existing_string(self) -> None:
        collection = IndexedCollection[str](["remove_me"])
        collection.remove("remove_me")
        assert len(collection) == 0

    def test_remove_nonexistent_float_raises_value_error(self) -> None:
        collection = IndexedCollection[float]([1.1])
        with pytest.raises(ValueError, match="not found"):
            collection.remove(2.2)

    def test_remove_different_items_same_hash(self) -> None:
        item1 = "first"
        item2 = "second"
        collection = IndexedCollection[str]([item1, "other"])
        item_hash = IndexedCollection.hash(item1)

        with patch(
            "sampletones_core.structures.collection.indexed.IndexedCollection.hash",
            return_value=item_hash,
        ):
            collection.remove(item2)
            assert len(collection) == 1

        assert "other" in collection
        assert item1 not in collection

    def test_remove_same_item_different_hash(self) -> None:
        with patch("sampletones_core.structures.collection.indexed.IndexedCollection.hash") as mock:
            mock.return_value = "hash_a"
            collection = IndexedCollection[str](["item"])

            mock.return_value = "hash_b"
            collection.append("item")

            mock.return_value = "hash_a"
            collection.remove("item")

            assert collection._items == {"hash_b": "item"}

    def test_remove_by_equivalent_item(self) -> None:
        collection = IndexedCollection[ValueObject]([ValueObject(value=1), ValueObject(value=2)])
        collection.remove(ValueObject(value=1))
        assert len(collection) == 1
        assert collection[0].value == 2


class TestIndex:
    def test_index_existing_integers(self) -> None:
        collection = IndexedCollection[int]([10, 20, 30])
        assert collection.index(10) == 0
        assert collection.index(20) == 1
        assert collection.index(30) == 2

    def test_index_existing_string(self) -> None:
        collection = IndexedCollection[str](["find_me"])
        assert collection.index("find_me") == 0

    def test_index_nonexistent_float_raises_value_error(self) -> None:
        collection = IndexedCollection[float]([1.1])
        with pytest.raises(ValueError, match="not found"):
            collection.index(2.2)

    def test_index_bytes_after_reordering(self) -> None:
        items = [b"a", b"b", b"c", b"d", b"e"]
        collection = IndexedCollection[bytes](items)
        del collection[1]
        assert collection.index(b"a") == 0
        assert collection.index(b"c") == 1
        assert collection.index(b"d") == 2


class TestHash:
    def test_hash_integer_static_method(self) -> None:
        hash1 = IndexedCollection.hash(42)
        hash2 = IndexedCollection.hash(42)
        assert hash1 == hash2
        assert isinstance(hash1, str)

    def test_hash_string_same_value_same_hash(self) -> None:
        hash1 = IndexedCollection.hash("test")
        hash2 = IndexedCollection.hash("test")
        assert hash1 == hash2

    def test_hash_float_different_values_different_hashes(self) -> None:
        hash1 = IndexedCollection.hash(1.1)
        hash2 = IndexedCollection.hash(2.2)
        assert hash1 != hash2

    def test_hash_bool_values(self) -> None:
        hash_true = IndexedCollection.hash(True)
        hash_false = IndexedCollection.hash(False)
        assert isinstance(hash_true, str)
        assert isinstance(hash_false, str)
        assert hash_true != hash_false


class TestGetHash:
    def test_get_hash_integer_by_positive_index(self) -> None:
        collection = IndexedCollection[int]([42])
        expected_hash = IndexedCollection.hash(42)
        assert collection.get_hash(0) == expected_hash

    def test_get_hash_string_by_negative_index(self) -> None:
        collection = IndexedCollection[str](["a", "b"])
        expected_hash = IndexedCollection.hash("b")
        assert collection.get_hash(-1) == expected_hash

    def test_get_hash_float_by_hash_string_validates_exists(self) -> None:
        collection = IndexedCollection[float]([3.14])
        item_hash = IndexedCollection.hash(3.14)
        assert collection.get_hash(item_hash) == item_hash

    def test_get_hash_nonexistent_hash_raises_key_error(self) -> None:
        collection = IndexedCollection[int]([1])
        with pytest.raises(KeyError, match="not found"):
            collection.get_hash("nonexistent")

    def test_get_hash_out_of_bounds_raises_index_error(self) -> None:
        collection = IndexedCollection[str](["only"])
        with pytest.raises(IndexError):
            collection.get_hash(10)

    def test_get_hash_wrong_type_raises_type_error(self) -> None:
        collection = IndexedCollection[bytes]([b"test"])
        with pytest.raises(TypeError):
            collection.get_hash(3.14)

    def test_get_hash_using_existing_hash_string_returns_same_hash(self) -> None:
        items = ["first", "second", "third"]
        collection = IndexedCollection[str](items)
        hash_second = IndexedCollection.hash("second")
        result = collection.get_hash(hash_second)
        assert result == hash_second

    def test_get_hash_using_nonexistent_hash_string_raises_key_error(self) -> None:
        collection = IndexedCollection[int]([10, 20, 30])
        fake_hash = "fake_hash"
        with pytest.raises(KeyError, match="not found"):
            collection.get_hash(fake_hash)


class TestGetIndex:
    def test_get_index_integer_by_positive_index(self) -> None:
        collection = IndexedCollection[int]([1])
        assert collection.get_index(0) == 0

    def test_get_index_string_by_negative_index(self) -> None:
        collection = IndexedCollection[str](["a", "b", "c"])
        assert collection.get_index(-1) == 2
        assert collection.get_index(-2) == 1

    def test_get_index_float_by_hash(self) -> None:
        collection = IndexedCollection[float]([1.1, 2.2])
        hash_second = IndexedCollection.hash(2.2)
        assert collection.get_index(hash_second) == 1

    def test_get_index_out_of_bounds_raises_index_error(self) -> None:
        collection = IndexedCollection[bytes]([b"test"])
        with pytest.raises(IndexError):
            collection.get_index(10)

    def test_get_index_nonexistent_hash_raises_key_error(self) -> None:
        collection = IndexedCollection[int]([1])
        with pytest.raises(KeyError):
            collection.get_index("fake_hash")

    def test_get_index_wrong_type_raises_type_error(self) -> None:
        collection = IndexedCollection[str](["test"])
        with pytest.raises(TypeError):
            collection.get_index([])


class TestHashCollisions:
    def test_hash_collision_integers_prevents_duplicate_insertion(self) -> None:
        collection = IndexedCollection[int]([1])

        with patch(
            "sampletones_core.structures.collection.indexed.IndexedCollection.hash",
            return_value=IndexedCollection.hash(1),
        ):
            with pytest.raises(ValueError, match="already exists"):
                collection.append(2)

    def test_hash_collision_strings_different_items_same_hash(self) -> None:
        with patch(
            "sampletones_core.structures.collection.indexed.IndexedCollection.hash",
            return_value="collision_hash",
        ):
            collection = IndexedCollection[str]()
            collection.append("first")
            with pytest.raises(ValueError, match="already exists"):
                collection.append("second")

    def test_access_by_colliding_hash(self) -> None:
        collection = IndexedCollection[float]([3.14])
        item_hash = IndexedCollection.hash(3.14)

        with patch(
            "sampletones_core.structures.collection.indexed.IndexedCollection.hash",
            return_value=item_hash,
        ):
            new_hash = IndexedCollection.hash(2.71)
            retrieved = collection[new_hash]
            assert 2.71 in collection
            assert retrieved == 3.14


class TestVerifyIntegrity:
    @staticmethod
    def verify_integrity(collection: IndexedCollection[HashableT]) -> None:
        item_keys = set(collection._items.keys())
        order_keys = set(collection._order.keys_forward())
        order_values = set(collection._order.values_forward())
        expected_values = set(range(len(collection)))

        assert item_keys == order_keys
        assert order_values == expected_values

    def test_items_and_order_same_keys_and_sequential_values_integers(self) -> None:
        collection = IndexedCollection[int]([1, 2, 3, 4, 5])
        self.verify_integrity(collection)

    def test_items_and_order_same_keys_and_sequential_values_strings(self) -> None:
        collection = IndexedCollection[str](["a", "b", "c", "d", "e"])
        self.verify_integrity(collection)

    def test_integrity_floats_after_insertions(self) -> None:
        collection = IndexedCollection[float]()
        for i in range(10):
            collection.append(float(i))
            self.verify_integrity(collection)

    def test_integrity_bytes_after_deletions(self) -> None:
        items = [b"a", b"b", b"c", b"d", b"e", b"f", b"g", b"h", b"i", b"j"]
        collection = IndexedCollection[bytes](items)
        for _ in range(5):
            collection.pop(0)
            self.verify_integrity(collection)

    def test_integrity_integers_after_mixed_operations(self) -> None:
        collection = IndexedCollection[int]()
        for i in range(5):
            collection.append(i)
        self.verify_integrity(collection)

        collection.pop(2)
        self.verify_integrity(collection)

        collection.insert(1, 99)
        self.verify_integrity(collection)

        del collection[0]
        self.verify_integrity(collection)

        collection.extend([100, 101, 102])
        self.verify_integrity(collection)

        collection.remove(99)
        self.verify_integrity(collection)

    def test_integrity_strings_after_setitem_operations(self) -> None:
        collection = IndexedCollection[str](["a", "b", "c", "d", "e"])
        self.verify_integrity(collection)
        collection[2] = "modified"
        self.verify_integrity(collection)

    def test_private_methods_can_desynchronize_structure(self) -> None:
        collection = IndexedCollection[int]([1, 2])
        collection._set(5, "fake_hash", 999, reindex=False)

        with pytest.raises(AssertionError):
            self.verify_integrity(collection)


class TestScenarios:
    def test_build_collection_integers_with_insertions_at_various_positions(self) -> None:
        collection = IndexedCollection[int]()
        collection.insert(0, 100)
        collection.insert(1, 300)
        collection.insert(1, 200)
        collection.insert(0, 50)

        assert list(collection) == [50, 100, 200, 300]

    def test_alternating_append_and_pop_operations_strings(self) -> None:
        collection = IndexedCollection[str]()
        for i in range(10):
            collection.append(f"item{i}")
            if i % 2 == 1:
                collection.pop(0)

        assert list(collection) == [f"item{i}" for i in range(5, 10)]

    def test_replace_all_items_floats_using_setitem_by_index(self) -> None:
        collection = IndexedCollection[float]([1.0, 2.0, 3.0])
        new_values = [4.0, 1.0, 2.0]
        for i, value in enumerate(new_values):
            collection[i] = value

        assert list(collection) == new_values

    def test_replace_all_items_bytes_using_setitem_by_hash(self) -> None:
        items = [b"a", b"b", b"c"]
        collection = IndexedCollection[bytes](items)
        hashes = [IndexedCollection.hash(item) for item in items]
        new_items = [b"x", b"y", b"z"]

        for old_hash, new_item in zip(hashes, new_items):
            collection[old_hash] = new_item

        assert list(collection) == new_items

    def test_setitem_integers_by_hash_of_removed_item(self) -> None:
        collection = IndexedCollection[int]([10, 20, 30])
        hash_20 = IndexedCollection.hash(20)
        del collection[1]

        with pytest.raises(KeyError):
            collection[hash_20] = 99

    def test_interleaved_access_strings_by_index_and_hash(self) -> None:
        items = ["a", "b", "c", "d", "e"]
        collection = IndexedCollection[str](items)

        assert collection[0] == "a"
        hash_c = IndexedCollection.hash("c")
        assert collection[hash_c] == "c"
        collection[hash_c] = "c'"
        with pytest.raises(KeyError):
            _ = collection[hash_c]

        assert collection[2] == "c'"
        assert collection[-1] == "e"

        hash_b = IndexedCollection.hash("b")
        del collection[hash_b]
        assert collection[0] == "a"
        assert collection[1] == "c'"
        assert collection[-1] == "e"

        collection.pop(-1)
        assert collection[-1] == "d"

    def test_copy_then_modify_both_collections_floats(self) -> None:
        original = IndexedCollection[float]([1.1, 2.2, 3.3])
        copy = original.copy()

        original.append(4.4)
        copy.append(5.5)

        # assert original[:3] == copy[:3]
        assert len(original) == 4
        assert len(copy) == 4
        assert original[-1] == 4.4
        assert copy[-1] == 5.5

    def test_clear_and_rebuild_integers_with_same_items(self) -> None:
        items = [1, 2, 3, 4, 5]
        collection = IndexedCollection[int](items)
        old_hashes = collection.hashes

        collection.clear()
        collection.extend(items)

        new_hashes = collection.hashes
        assert old_hashes == new_hashes
        for i, item in enumerate(items):
            assert collection[old_hashes[i]] == item
            assert collection[i] == item

    def test_remove_items_strings_in_reverse_order(self) -> None:
        items = ["a", "b", "c", "d", "e"]
        collection = IndexedCollection[str](items)
        for _ in range(len(items)):
            collection.pop(-1)
            assert list(collection) == items[: len(collection)]

    def test_insert_at_every_position_bytes_in_growing_collection(self) -> None:
        collection = IndexedCollection[bytes]()
        for i in range(5):
            collection.insert(0, bytes([i]))

        expected = [bytes([i]) for i in range(4, -1, -1)]
        assert list(collection) == expected


class TestHashAccess:
    def test_setitem_integers_by_nonexistent_hash_raises_key_error(self) -> None:
        collection = IndexedCollection[int]([1])
        with pytest.raises(KeyError):
            collection["nonexistent_hash"] = 2

    def test_setitem_strings_by_hash_updates_same_position(self) -> None:
        items = ["a", "b", "c"]
        collection = IndexedCollection[str](items)
        hash_b = IndexedCollection.hash("b")
        collection[hash_b] = "new"

        assert list(collection) == ["a", "new", "c"]
        assert "b" not in collection

    def test_setitem_floats_by_hash_removes_old_hash_adds_new_hash(self) -> None:
        collection = IndexedCollection[float]([1.1, 2.2])
        old_hash = IndexedCollection.hash(1.1)
        new_hash = IndexedCollection.hash(3.3)

        collection[old_hash] = 3.3

        assert collection[new_hash] == 3.3
        with pytest.raises(KeyError):
            _ = collection[old_hash]

    def test_access_bytes_by_hash_after_item_moved(self) -> None:
        items = [b"a", b"b", b"c"]
        collection = IndexedCollection[bytes](items)
        hash_c = IndexedCollection.hash(b"c")

        del collection[0]

        assert collection[hash_c] == b"c"
        assert collection.get_index(hash_c) == 1

    def test_pop_strings_by_hash_returns_correct_item(self) -> None:
        items = ["first", "second", "third"]
        collection = IndexedCollection[str](items)
        hash_second = IndexedCollection.hash("second")
        popped = collection.pop(hash_second)

        assert popped == "second"
        assert len(collection) == 2


class TestEdgeCases:
    def test_large_collection_integers_operations(self) -> None:
        items = list(range(1000))
        collection = IndexedCollection[int](items)
        assert len(collection) == 1000
        assert collection[0] == 0
        assert collection[-1] == 999
        assert collection[500] == 500

    def test_single_item_string_collection_operations(self) -> None:
        collection = IndexedCollection[str](["single"])
        assert collection[0] == "single"
        assert collection[-1] == "single"
        popped = collection.pop()
        assert popped == "single"
        assert len(collection) == 0

    def test_modify_different_items_of_same_hash(self) -> None:
        common_item = ValueObject(value=1)
        first_item = ValueObject(value=2)
        second_item = ValueObject(value=2)
        collection1 = IndexedCollection[ValueObject]([common_item, first_item])
        collection2 = IndexedCollection[ValueObject]([common_item, second_item])
        assert collection1 == collection2
        assert collection1[0] is collection2[0]
        assert collection1[1] is not collection2[1]
        assert common_item in collection1
        assert common_item in collection2

        common_item.value = 5
        assert collection1 == collection2
        assert common_item not in collection1  # hash changed, should not happen in real usage

        collection1[0] = ValueObject(value=3)
        collection2[0] = ValueObject(value=3)
        assert collection1 == collection2

    def test_mutable_model_in_collection_changes_hash(self) -> None:
        item = ValueObject(value=1)
        collection = IndexedCollection[ValueObject]([item])
        assert item in collection

        item.value = 2
        assert collection[0] is item
        assert item not in collection  # the item is NOT in the collection; hash got out of sync

    def test_models_in_collection(self) -> None:
        items = [ValueObject(value=i) for i in range(5)]
        collection = IndexedCollection[ValueObject](items)
        assert collection[2].value == 2
        collection[2] = ValueObject(value=99)
        assert collection[2].value == 99

    def test_adding_non_serializable_model(self) -> None:
        item = NonSerializableModel(data={"complex": "data"})
        collection = IndexedCollection[NonSerializableModel]([0])
        with pytest.raises(TypeError, match="unhashable"):
            collection.append(item)

    def test_zero_values_different_types(self) -> None:
        collection = IndexedCollection[Hashable]([0])
        with pytest.raises(ValueError, match="already exists"):
            collection.append(False)

        # Depends on the hash function implementation
        new_items = [item for item in [0.0, False, b"\00"] if IndexedCollection.hash(0) != IndexedCollection.hash(item)]
        collection.extend(new_items)


class TestSetItemSamePosition:
    def test_setitem_same_hash_same_position_replaces(self) -> None:
        collection = IndexedCollection[str](["apple", "banana", "cherry"])
        original_item = collection[1]
        assert original_item == "banana"

        item_hash = IndexedCollection.hash(original_item)
        collection[item_hash] = "BANANA"

        assert collection[1] == "BANANA"
        assert len(collection) == 3

    def test_setitem_by_index_same_hash_replaces(self) -> None:
        collection = IndexedCollection[int]([10, 20, 30])
        collection[1] = 20
        assert collection[1] == 20
        assert len(collection) == 3

    def test_setitem_same_position_preserves_order(self) -> None:
        items = ["a", "b", "c", "d"]
        collection = IndexedCollection[str](items)
        collection[2] = "c"
        assert list(collection) == items


class TestIteratorNext:
    def test_next_returns_first_item(self) -> None:
        collection = IndexedCollection[str](["first", "second", "third"])
        result = next(collection)
        assert result == "first"

    def test_next_on_empty_raises_stop_iteration(self) -> None:
        collection = IndexedCollection[int]()
        with pytest.raises(StopIteration):
            next(collection)


class TestGetKeyError:
    def test_get_with_key_error_returns_default(self) -> None:
        collection = IndexedCollection[str](["test"])
        fake_hash = "nonexistent"
        result = collection.get(fake_hash, "default")
        assert result == "default"

    def test_get_with_index_error_returns_default(self) -> None:
        collection = IndexedCollection[int]([1, 2, 3])
        result = collection.get(10, -1)
        assert result == -1
