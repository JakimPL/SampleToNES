from typing import Union

import pytest

from sampletones.utils.collections.bidirectional import BidirectionalHashMap
from tests.sampletones.dummy import CollisionObject, ValueObject


class TestInitialization:
    def test_init_empty(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        assert len(bidirectional) == 0
        assert repr(bidirectional) == "BidirectionalHashMap({})"

    def test_init_with_valid_forward_mapping(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1, "b": 2})
        assert len(bidirectional) == 2
        assert bidirectional["a"] == 1
        assert bidirectional[1] == "a"
        assert bidirectional["b"] == 2
        assert bidirectional[2] == "b"

    def test_init_with_valid_backward_mapping(self) -> None:
        bidirectional = BidirectionalHashMap[int]({1: "a", 2: "b"})
        assert len(bidirectional) == 2
        assert bidirectional["a"] == 1
        assert bidirectional[1] == "a"

    def test_init_with_mixed_mapping(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1, 2: "b"})
        assert len(bidirectional) == 2
        assert bidirectional["a"] == 1
        assert bidirectional["b"] == 2

    def test_init_with_string_value_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            BidirectionalHashMap[int]({"a": "b"})

    def test_init_with_conflicting_mapping_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            BidirectionalHashMap[int]({"a": 1, "b": 1})


class TestGetItem:
    def test_getitem_forward_existing_key(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        assert bidirectional["a"] == 1

    def test_getitem_backward_existing_value(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        assert bidirectional[1] == "a"

    def test_getitem_forward_missing_key_raises_key_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        with pytest.raises(KeyError, match="Key/value 'missing' not found"):
            _ = bidirectional["missing"]

    def test_getitem_backward_missing_value_raises_key_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        with pytest.raises(KeyError, match="Key/value '999' not found"):
            _ = bidirectional[999]


class TestSetItem:
    def test_setitem_forward_new_mapping(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        bidirectional["a"] = 1
        assert bidirectional["a"] == 1
        assert bidirectional[1] == "a"
        assert len(bidirectional) == 1

    def test_setitem_backward_new_mapping(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        bidirectional[1] = "a"
        assert bidirectional["a"] == 1
        assert bidirectional[1] == "a"
        assert len(bidirectional) == 1

    def test_setitem_forward_update_existing_key(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        bidirectional["a"] = 2
        assert bidirectional["a"] == 2
        assert bidirectional[2] == "a"
        assert len(bidirectional) == 1

    def test_setitem_backward_update_existing_value(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        bidirectional[1] = "b"
        assert bidirectional["b"] == 1
        assert bidirectional[1] == "b"
        assert len(bidirectional) == 1

    def test_setitem_string_value_raises_type_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        with pytest.raises(TypeError):
            bidirectional["a"] = "b"

    def test_setitem_both_non_string_raises_type_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        with pytest.raises(TypeError):
            bidirectional[1] = 2

    def test_setitem_value_already_mapped_raises_value_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        with pytest.raises(ValueError, match="Value 1 is already mapped to the key a"):
            bidirectional["b"] = 1


class TestDelItem:
    def test_delitem_forward_existing_key(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1, "b": 2})
        del bidirectional["a"]
        assert len(bidirectional) == 1
        with pytest.raises(KeyError):
            _ = bidirectional["a"]
        with pytest.raises(KeyError):
            _ = bidirectional[1]

    def test_delitem_backward_existing_value(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1, "b": 2})
        del bidirectional[1]
        assert len(bidirectional) == 1
        with pytest.raises(KeyError):
            _ = bidirectional["a"]
        with pytest.raises(KeyError):
            _ = bidirectional[1]

    def test_delitem_forward_missing_key_raises_key_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        with pytest.raises(KeyError):
            del bidirectional["missing"]

    def test_delitem_backward_missing_value_raises_key_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        with pytest.raises(KeyError):
            del bidirectional[999]


class TestLen:
    def test_len_empty(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        assert len(bidirectional) == 0

    def test_len_with_items(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1, "b": 2, "c": 3})
        assert len(bidirectional) == 3


class TestRepr:
    def test_repr(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        assert repr(bidirectional) == "BidirectionalHashMap({'a': 1})"


class TestSetForward:
    def test_set_forward_new_mapping(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        bidirectional.set_forward("a", 1)
        assert bidirectional["a"] == 1
        assert bidirectional[1] == "a"

    def test_set_forward_update_existing_key_new_value(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        bidirectional.set_forward("a", 2)
        assert bidirectional["a"] == 2
        assert bidirectional[2] == "a"
        with pytest.raises(KeyError):
            _ = bidirectional[1]

    def test_set_forward_same_key_same_value(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        bidirectional.set_forward("a", 1)
        assert bidirectional["a"] == 1
        assert bidirectional[1] == "a"

    def test_set_forward_non_string_key_raises_type_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        with pytest.raises(TypeError, match="Key must be a str"):
            bidirectional.set_forward(123, 1)  # type: ignore

    def test_set_forward_string_value_raises_type_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        with pytest.raises(TypeError, match="Value must not be a str"):
            bidirectional.set_forward("a", "b")  # type: ignore

    def test_set_forward_value_already_mapped_raises_value_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        with pytest.raises(ValueError, match="Value 1 is already mapped to the key a"):
            bidirectional.set_forward("b", 1)


class TestSetBackward:
    def test_set_backward_new_mapping(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        bidirectional.set_backward(1, "a")
        assert bidirectional["a"] == 1
        assert bidirectional[1] == "a"

    def test_set_backward_update_existing_value_new_key(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        bidirectional.set_backward(1, "b")
        assert bidirectional["b"] == 1
        assert bidirectional[1] == "b"
        with pytest.raises(KeyError):
            _ = bidirectional["a"]

    def test_set_backward_same_value_same_key(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        bidirectional.set_backward(1, "a")
        assert bidirectional["a"] == 1
        assert bidirectional[1] == "a"

    def test_set_backward_non_string_key_raises_type_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        with pytest.raises(TypeError, match="Key must be a str"):
            bidirectional.set_backward(1, 123)  # type: ignore

    def test_set_backward_string_value_raises_type_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        with pytest.raises(TypeError, match="Value must not be a str"):
            bidirectional.set_backward("a", "b")  # type: ignore

    def test_set_backward_key_already_bound_raises_value_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        with pytest.raises(ValueError, match="Key a is already bound to the value 1"):
            bidirectional.set_backward(2, "a")


class TestSet:
    def test_set_forward_direction(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        bidirectional.set("a", 1)
        assert bidirectional["a"] == 1
        assert bidirectional[1] == "a"

    def test_set_backward_direction(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        bidirectional.set(1, "a")
        assert bidirectional["a"] == 1
        assert bidirectional[1] == "a"


class TestUpdate:
    def test_update_with_forward_mappings(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        bidirectional.update({"a": 1, "b": 2})
        assert bidirectional["a"] == 1
        assert bidirectional["b"] == 2

    def test_update_with_backward_mappings(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        bidirectional.update({1: "a", 2: "b"})
        assert bidirectional["a"] == 1
        assert bidirectional["b"] == 2

    def test_update_with_mixed_mappings(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        bidirectional.update({"a": 1, 2: "b"})
        assert bidirectional["a"] == 1
        assert bidirectional["b"] == 2

    def test_update_with_invalid_mapping_raises_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        with pytest.raises(TypeError):
            bidirectional.update({"a": "b"})


class TestUpdateForward:
    def test_update_forward_multiple_mappings(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        bidirectional.update_forward({"a": 1, "b": 2, "c": 3})
        assert len(bidirectional) == 3
        assert bidirectional["a"] == 1
        assert bidirectional["b"] == 2
        assert bidirectional["c"] == 3

    def test_update_forward_empty_mapping(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        bidirectional.update_forward({})
        assert len(bidirectional) == 1


class TestUpdateBackward:
    def test_update_backward_multiple_mappings(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        bidirectional.update_backward({1: "a", 2: "b", 3: "c"})
        assert len(bidirectional) == 3
        assert bidirectional["a"] == 1
        assert bidirectional["b"] == 2
        assert bidirectional["c"] == 3

    def test_update_backward_empty_mapping(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        bidirectional.update_backward({})
        assert len(bidirectional) == 1


class TestGet:
    def test_get_forward_existing_key(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        assert bidirectional.get("a") == 1

    def test_get_backward_existing_value(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        assert bidirectional.get(1) == "a"

    def test_get_forward_missing_key_returns_none(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        assert bidirectional.get("missing") is None

    def test_get_backward_missing_value_returns_none(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        assert bidirectional.get(999) is None


class TestForward:
    def test_forward_existing_key(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        assert bidirectional.forward("a") == 1

    def test_forward_missing_key_raises_key_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        with pytest.raises(KeyError):
            bidirectional.forward("missing")

    def test_forward_non_string_key_raises_type_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        with pytest.raises(TypeError, match="Key must be a str"):
            bidirectional.forward(123)  # type: ignore


class TestBackward:
    def test_backward_existing_value(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        assert bidirectional.backward(1) == "a"

    def test_backward_missing_value_raises_key_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        with pytest.raises(KeyError):
            bidirectional.backward(999)


class TestPop:
    def test_pop_forward_existing_key(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1, "b": 2})
        result = bidirectional.pop("a")
        assert result == 1
        assert len(bidirectional) == 1
        with pytest.raises(KeyError):
            _ = bidirectional["a"]

    def test_pop_backward_existing_value(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1, "b": 2})
        result = bidirectional.pop(1)
        assert result == "a"
        assert len(bidirectional) == 1
        with pytest.raises(KeyError):
            _ = bidirectional[1]

    def test_pop_forward_missing_key_raises_key_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        with pytest.raises(KeyError, match="Key/value 'missing' not found"):
            bidirectional.pop("missing")

    def test_pop_backward_missing_value_raises_key_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        with pytest.raises(KeyError, match="Key/value '999' not found"):
            bidirectional.pop(999)


class TestPopForward:
    def test_pop_forward_existing_key(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1, "b": 2})
        result = bidirectional.pop_forward("a")
        assert result == 1
        assert len(bidirectional) == 1
        with pytest.raises(KeyError):
            _ = bidirectional["a"]
        with pytest.raises(KeyError):
            _ = bidirectional[1]

    def test_pop_forward_missing_key_raises_key_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        with pytest.raises(KeyError):
            bidirectional.pop_forward("missing")

    def test_pop_forward_removes_both_mappings(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        bidirectional.pop_forward("a")
        assert bidirectional.get("a") is None
        assert bidirectional.get(1) is None


class TestPopBackward:
    def test_pop_backward_existing_value(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1, "b": 2})
        result = bidirectional.pop_backward(1)
        assert result == "a"
        assert len(bidirectional) == 1
        with pytest.raises(KeyError):
            _ = bidirectional["a"]
        with pytest.raises(KeyError):
            _ = bidirectional[1]

    def test_pop_backward_missing_value_raises_key_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        with pytest.raises(KeyError):
            bidirectional.pop_backward(999)

    def test_pop_backward_removes_both_mappings(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        bidirectional.pop_backward(1)
        assert bidirectional.get("a") is None
        assert bidirectional.get(1) is None


class TestRemap:
    def test_remap_forward_both_strings(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        bidirectional.remap("a", "b")
        assert bidirectional["b"] == 1
        assert bidirectional[1] == "b"
        with pytest.raises(KeyError):
            _ = bidirectional["a"]

    def test_remap_backward_both_non_strings(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        bidirectional.remap(1, 2)
        assert bidirectional["a"] == 2
        assert bidirectional[2] == "a"
        with pytest.raises(KeyError):
            _ = bidirectional[1]

    def test_remap_mismatched_types_raises_type_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        with pytest.raises(TypeError, match="must be of the same type"):
            bidirectional.remap("a", 2)


class TestRemapForward:
    def test_remap_forward_existing_key_to_new_key(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        bidirectional.remap_forward("a", "b")
        assert bidirectional["b"] == 1
        assert bidirectional[1] == "b"
        assert len(bidirectional) == 1
        with pytest.raises(KeyError):
            _ = bidirectional["a"]

    def test_remap_forward_missing_old_key_raises_key_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        with pytest.raises(KeyError):
            bidirectional.remap_forward("missing", "new")

    def test_remap_forward_to_same_key(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1, "b": 2})
        bidirectional.remap_forward("a", "a")
        assert bidirectional["a"] == 1
        assert len(bidirectional) == 2


class TestRemapBackward:
    def test_remap_backward_existing_value_to_new_value(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        bidirectional.remap_backward(1, 2)
        assert bidirectional["a"] == 2
        assert bidirectional[2] == "a"
        assert len(bidirectional) == 1
        with pytest.raises(KeyError):
            _ = bidirectional[1]

    def test_remap_backward_missing_old_value_raises_key_error(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        with pytest.raises(KeyError):
            bidirectional.remap_backward(999, 1000)


class TestScenarios:
    def test_multiple_updates_and_deletions(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        bidirectional["a"] = 1
        bidirectional["b"] = 2
        bidirectional["c"] = 3
        assert len(bidirectional) == 3

        del bidirectional["b"]
        assert len(bidirectional) == 2

        bidirectional["a"] = 4
        assert bidirectional["a"] == 4
        assert bidirectional[4] == "a"
        with pytest.raises(KeyError):
            _ = bidirectional[1]

    def test_chain_of_remappings(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        bidirectional.remap_forward("a", "b")
        bidirectional.remap_forward("b", "c")
        bidirectional.remap_backward(1, 2)
        assert bidirectional["c"] == 2
        assert bidirectional[2] == "c"

    def test_interleaved_forward_and_backward_operations(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        bidirectional["a"] = 1
        bidirectional[2] = "b"
        bidirectional.set_forward("c", 3)
        bidirectional.set_backward(4, "d")

        assert bidirectional["a"] == 1
        assert bidirectional["b"] == 2
        assert bidirectional["c"] == 3
        assert bidirectional["d"] == 4
        assert len(bidirectional) == 4

    def test_update_replaces_old_mappings(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1, "b": 2})
        bidirectional["a"] = 3
        assert bidirectional["a"] == 3
        assert bidirectional[3] == "a"
        assert bidirectional.get(1) is None

    def test_backward_update_replaces_old_mappings(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1, "b": 2})
        bidirectional[1] = "c"
        assert bidirectional["c"] == 1
        assert bidirectional[1] == "c"
        assert bidirectional.get("a") is None


class TestClear:
    def test_clear_empty_map(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        bidirectional.clear()
        assert len(bidirectional) == 0

    def test_clear_populated_map(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1, "b": 2, "c": 3})
        assert len(bidirectional) == 3
        bidirectional.clear()
        assert len(bidirectional) == 0
        assert bidirectional.get("a") is None
        assert bidirectional.get(1) is None

    def test_operations_after_clear(self) -> None:
        bidirectional = BidirectionalHashMap[int]({"a": 1})
        bidirectional.clear()
        bidirectional["x"] = 99
        assert bidirectional["x"] == 99
        assert bidirectional[99] == "x"
        assert len(bidirectional) == 1


class TestTypes:
    def test_tuple_as_value(self) -> None:
        bidirectional = BidirectionalHashMap[tuple[int, ...]]()
        bidirectional["point"] = (1, 2, 3)
        assert bidirectional["point"] == (1, 2, 3)
        assert bidirectional[(1, 2, 3)] == "point"

    def test_frozenset_as_value(self) -> None:
        bidirectional = BidirectionalHashMap[frozenset[str]]()
        value = frozenset({"a", "b", "c"})
        bidirectional["set1"] = value
        assert bidirectional["set1"] == value
        assert bidirectional[value] == "set1"

    def test_none_as_value(self) -> None:
        bidirectional = BidirectionalHashMap[None]()
        bidirectional["null"] = None
        assert bidirectional["null"] is None
        assert bidirectional[None] == "null"

    def test_bool_as_value(self) -> None:
        bidirectional = BidirectionalHashMap[bool]()
        bidirectional["true"] = True
        bidirectional["false"] = False
        assert bidirectional["true"] is True
        assert bidirectional[True] == "true"
        assert bidirectional["false"] is False
        assert bidirectional[False] == "false"

    def test_complex_number_as_value(self) -> None:
        bidirectional = BidirectionalHashMap[complex]()
        bidirectional["imaginary"] = 3 + 4j
        assert bidirectional["imaginary"] == 3 + 4j
        assert bidirectional[3 + 4j] == "imaginary"

    def test_bytes_as_value(self) -> None:
        bidirectional = BidirectionalHashMap[bytes]()
        bidirectional["data"] = b"hello"
        assert bidirectional["data"] == b"hello"
        assert bidirectional[b"hello"] == "data"

    def test_list_as_value_raises_type_error(self) -> None:
        bidirectional = BidirectionalHashMap()
        with pytest.raises(TypeError):
            bidirectional["list"] = [1, 2, 3]

    def test_set_as_value_raises_type_error(self) -> None:
        bidirectional = BidirectionalHashMap()
        with pytest.raises(TypeError):
            bidirectional["set"] = {1, 2, 3}

    def test_dict_as_value_raises_type_error(self) -> None:
        bidirectional = BidirectionalHashMap()
        with pytest.raises(TypeError):
            bidirectional["dict"] = {"a": 1}

    def test_mixed_numeric_types(self) -> None:
        bidirectional = BidirectionalHashMap[Union[int, float]]()
        bidirectional["int"] = 42
        bidirectional["float"] = 3.14
        assert bidirectional["int"] == 42
        assert bidirectional[42] == "int"
        assert bidirectional["float"] == 3.14
        assert bidirectional[3.14] == "float"

    def test_enum_like_usage(self) -> None:
        from enum import Enum

        class Status(Enum):
            PENDING = 1
            APPROVED = 2
            REJECTED = 3

        bidirectional = BidirectionalHashMap[Status]()
        bidirectional["pending"] = Status.PENDING
        bidirectional["approved"] = Status.APPROVED
        bidirectional["rejected"] = Status.REJECTED

        assert bidirectional["pending"] == Status.PENDING
        assert bidirectional[Status.APPROVED] == "approved"
        assert len(bidirectional) == 3


class TestEdgeCases:
    def test_hash_collision_objects(self) -> None:
        bidirectional = BidirectionalHashMap[CollisionObject]()
        obj1 = CollisionObject(1)
        obj2 = CollisionObject(2)

        bidirectional["first"] = obj1
        bidirectional["second"] = obj2

        assert bidirectional["first"] == obj1
        assert bidirectional["second"] == obj2
        assert bidirectional[obj1] == "first"
        assert bidirectional[obj2] == "second"
        assert len(bidirectional) == 2

    def test_numeric_type_coercion_false_zero_zero_float(self) -> None:
        bidirectional = BidirectionalHashMap[int | float | bool]()
        bidirectional["zero_int"] = 0

        with pytest.raises(ValueError, match="Value False is already mapped to the key zero_int"):
            bidirectional["false_bool"] = False

        with pytest.raises(ValueError, match="Value 0.0 is already mapped to the key zero_int"):
            bidirectional["zero_float"] = 0.0

        assert len(bidirectional) == 1
        assert bidirectional[0] == "zero_int"
        assert bidirectional[False] == "zero_int"
        assert bidirectional[0.0] == "zero_int"

    def test_enum_vs_int_with_same_value(self) -> None:
        from enum import Enum

        class Status(Enum):
            INITIAL = 0
            ACTIVE = 1

        bidirectional = BidirectionalHashMap[int | Status]()
        bidirectional["int_zero"] = 0
        bidirectional["enum_zero"] = Status.INITIAL

        assert len(bidirectional) == 2
        assert bidirectional["int_zero"] == 0
        assert bidirectional["enum_zero"] == Status.INITIAL
        assert bidirectional[0] == "int_zero"
        assert bidirectional[Status.INITIAL] == "enum_zero"

    def test_intenum_vs_int_with_same_value(self) -> None:
        from enum import IntEnum

        class Priority(IntEnum):
            LOW = 0
            MEDIUM = 1
            HIGH = 2

        bidirectional = BidirectionalHashMap[int | Priority]()
        bidirectional["int_zero"] = 0

        with pytest.raises(ValueError, match="is already mapped to the key int_zero"):
            bidirectional["enum_zero"] = Priority.LOW

        assert len(bidirectional) == 1
        assert bidirectional[0] == "int_zero"
        assert bidirectional[Priority.LOW] == "int_zero"

    def test_object_equality_causes_collision(self) -> None:
        bidirectional = BidirectionalHashMap[ValueObject]()
        first = ValueObject(42)
        second = ValueObject(42)

        bidirectional["first"] = first

        with pytest.raises(ValueError, match="is already mapped to the key first"):
            bidirectional["second"] = second

        assert len(bidirectional) == 1
        assert bidirectional[first] == "first"
        assert bidirectional[second] == "first"

    def test_object_identity_no_collision(self) -> None:
        class IdentityObject:
            def __init__(self, value: int) -> None:
                self.value = value

            def __hash__(self) -> int:
                return id(self)

            def __eq__(self, other: object) -> bool:
                return self is other

        bidirectional = BidirectionalHashMap[IdentityObject]()
        first = IdentityObject(42)
        second = IdentityObject(42)

        bidirectional["first"] = first
        bidirectional["second"] = second

        assert len(bidirectional) == 2
        assert bidirectional[first] == "first"
        assert bidirectional[second] == "second"
        assert bidirectional["first"] is first
        assert bidirectional["second"] is second

    def test_whitespace_only_keys(self) -> None:
        bidirectional = BidirectionalHashMap[int]()
        bidirectional[" "] = 1
        bidirectional["  "] = 2
        bidirectional["\t"] = 3
        bidirectional["\n"] = 4

        assert len(bidirectional) == 4
        assert bidirectional[1] == " "
        assert bidirectional[2] == "  "

    def test_negative_zero_vs_positive_zero(self) -> None:
        bidirectional = BidirectionalHashMap[float]()
        bidirectional["pos_zero"] = 0.0

        with pytest.raises(ValueError, match="Value -0.0 is already mapped"):
            bidirectional["neg_zero"] = -0.0

        bidirectional[-0.0] = "neg_zero"

        assert len(bidirectional) == 1
        assert bidirectional["neg_zero"] == 0.0
        assert bidirectional[0.0] == "neg_zero"
        assert bidirectional[-0.0] == "neg_zero"

    def test_nan_value_handling(self) -> None:
        bidirectional = BidirectionalHashMap[float]()
        nan1 = float("nan")
        nan2 = float("nan")

        bidirectional["nan1"] = nan1
        bidirectional["nan2"] = nan2

        assert len(bidirectional) == 2
        assert bidirectional["nan1"] is nan1
        assert bidirectional["nan2"] is nan2

    def test_infinity_values(self) -> None:
        bidirectional = BidirectionalHashMap[float]()
        bidirectional["pos_inf"] = float("inf")
        bidirectional["neg_inf"] = float("-inf")

        assert len(bidirectional) == 2
        assert bidirectional[float("inf")] == "pos_inf"
        assert bidirectional[float("-inf")] == "neg_inf"

    def test_frozenset_order_independence(self) -> None:
        bidirectional = BidirectionalHashMap[frozenset[int]]()
        set1 = frozenset([1, 2, 3])
        set2 = frozenset([3, 2, 1])

        bidirectional["first"] = set1

        with pytest.raises(ValueError, match="is already mapped to the key first"):
            bidirectional["second"] = set2

        assert len(bidirectional) == 1
        assert bidirectional[frozenset([1, 2, 3])] == "first"
        assert bidirectional[frozenset([3, 2, 1])] == "first"
