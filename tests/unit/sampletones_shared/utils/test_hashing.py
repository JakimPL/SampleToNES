import pytest

from sampletones_shared.utils.hashing import (
    HASH_LENGTH,
    IDENTITY_SEPARATOR,
    calculate_hash,
    hash_model,
    hash_models,
    identity_digest,
)
from tests.suite.dummy import NestedModel, SimpleModel


class TestCalculateHash:
    def test_hash_string(self) -> None:
        hash1 = calculate_hash("test")
        hash2 = calculate_hash("test".encode("utf-8"))
        hash3 = calculate_hash(b"test")
        hash4 = calculate_hash("different")

        assert hash1 == hash2
        assert hash1 == hash3
        assert hash1 != hash4
        assert isinstance(hash1, str)
        assert len(hash1) == HASH_LENGTH

    def test_hash_integer(self) -> None:
        hash1 = calculate_hash(42)
        hash2 = calculate_hash(42)
        hash3 = calculate_hash(1)

        assert hash1 == hash2
        assert hash1 != hash3
        assert isinstance(hash1, str)

    def test_hash_float(self) -> None:
        hash1 = calculate_hash(3.14)
        hash2 = calculate_hash(3.14)
        hash3 = calculate_hash(2.71)

        assert hash1 == hash2
        assert hash1 != hash3
        assert isinstance(hash1, str)

    def test_hash_bytes(self) -> None:
        hash1 = calculate_hash(b"same")
        hash2 = calculate_hash(b"same")
        hash3 = calculate_hash(b"different")

        assert hash1 == hash2
        assert hash1 != hash3
        assert isinstance(hash1, str)

    def test_hash_bytes_same_as_strings(self) -> None:
        hash1 = calculate_hash(b"data")
        hash2 = calculate_hash("data")
        hash3 = calculate_hash("data".encode("utf-8"))

        assert hash1 == hash2
        assert hash1 == hash3

    def test_hash_boolean(self) -> None:
        hash1 = calculate_hash(True)
        hash2 = calculate_hash(True)
        hash3 = calculate_hash(False)

        assert hash1 == hash2
        assert hash1 != hash3
        assert isinstance(hash1, str)

    def test_hash_null_different_representations(self) -> None:
        hash_false = calculate_hash(False)
        hash_zero = calculate_hash(0)
        hash_float_zero = calculate_hash(0.0)
        hash_empty_string = calculate_hash("")
        hash_null_bytes = calculate_hash(b"")
        hash_none = calculate_hash(None)

        assert hash_false == hash_zero
        assert hash_false == hash_float_zero
        assert hash_false == hash_null_bytes
        assert hash_false == hash_empty_string
        assert hash_false != hash_none

    def test_hash_base_model(self) -> None:
        model1 = SimpleModel(value=42, name="test")
        model2 = SimpleModel(value=42, name="test")

        hash1 = calculate_hash(model1)
        hash2 = calculate_hash(model2)

        assert hash1 == hash2

    def test_hash_different_base_models(self) -> None:
        model1 = SimpleModel(value=1, name="test")
        model2 = SimpleModel(value=1, name="test")
        model3 = SimpleModel(value=2, name="test")

        hash1 = calculate_hash(model1)
        hash2 = calculate_hash(model2)
        hash3 = calculate_hash(model3)

        assert hash1 == hash2
        assert hash1 != hash3

    def test_hash_custom_length(self) -> None:
        hash_16 = calculate_hash("test", length=16)
        hash_64 = calculate_hash("test", length=64)

        assert hash_16 != hash_64
        assert len(hash_16) == 16
        assert len(hash_64) == 64
        assert hash_64.startswith(hash_16)

    def test_hash_zero_length_raises(self) -> None:
        with pytest.raises(ValueError):
            calculate_hash("test", length=0)

    def test_hash_excessive_length_raises(self) -> None:
        with pytest.raises(ValueError):
            calculate_hash("test", length=65)

    def test_hash_tuple(self) -> None:
        hash1 = calculate_hash((1, 2, 3))
        hash2 = calculate_hash((1, 2, 3))

        assert hash1 == hash2

    def test_hash_frozenset(self) -> None:
        hash1 = calculate_hash(frozenset([1, 2, 3]))
        hash2 = calculate_hash(frozenset([1, 2, 3]))
        hash3 = calculate_hash(frozenset([3, 2, 1]))

        assert hash1 == hash2
        assert hash1 == hash3
        assert isinstance(hash1, str)


class TestHashModels:
    def test_hash_single_model(self) -> None:
        model = SimpleModel(value=42, name="test")
        hash1 = hash_model(model)
        hash2 = hash_model(model)

        assert hash1 == hash2
        assert isinstance(hash1, str)
        assert len(hash1) == HASH_LENGTH

    def test_hash_different_single_models(self) -> None:
        model1 = SimpleModel(value=1, name="test1")
        model2 = SimpleModel(value=2, name="test2")

        hash1 = hash_model(model1)
        hash2 = hash_model(model2)

        assert hash1 != hash2

    def test_hash_multiple_models(self) -> None:
        model1 = SimpleModel(value=1, name="first")
        model2 = SimpleModel(value=2, name="second")

        hash1 = hash_models(model1, model2)
        hash2 = hash_models(model1, model2)

        assert hash1 == hash2

    def test_hash_multiple_models_order_matters(self) -> None:
        model1 = SimpleModel(value=1, name="first")
        model2 = SimpleModel(value=2, name="second")

        hash_forward = hash_models(model1, model2)
        hash_backward = hash_models(model2, model1)

        assert hash_forward != hash_backward

    def test_hash_single_vs_multiple(self) -> None:
        model = SimpleModel(value=42, name="test")

        hash_single = hash_model(model)
        hash_multiple = hash_models(model)

        assert hash_single == hash_multiple

    def test_hash_nested_model(self) -> None:
        inner = SimpleModel(value=1, name="inner")
        outer = NestedModel(simple=inner, items=[1, 2, 3])

        hash1 = hash_model(outer)
        hash2 = hash_model(outer)

        assert hash1 == hash2

    def test_hash_models_custom_length(self) -> None:
        model = SimpleModel(value=42, name="test")

        hash_16 = hash_model(model, length=16)
        hash_64 = hash_model(model, length=64)

        assert len(hash_16) == 16
        assert len(hash_64) == 64

    def test_hash_models_many(self) -> None:
        models = [SimpleModel(value=i, name=f"model{i}") for i in range(10)]

        hash1 = hash_models(*models)
        hash2 = hash_models(*models)

        assert hash1 == hash2


class TestEdgeCases:
    def test_calculate_hash_list_raises(self) -> None:
        with pytest.raises(TypeError):
            calculate_hash([1, 2, 3])

    def test_calculate_hash_dict_raises(self) -> None:
        with pytest.raises(TypeError):
            calculate_hash({"key": "value"})


class TestIdentityDigest:
    def test_digest_repeats_for_one_identity(self) -> None:
        assert identity_digest("folder", "take") == identity_digest("folder", "take")

    def test_identities_spelled_apart_digest_apart(self) -> None:
        assert identity_digest("folder", "take") != identity_digest("folder_take")

    def test_the_order_the_parts_stand_in_settles_the_digest(self) -> None:
        assert identity_digest("folder", "take") != identity_digest("take", "folder")

    def test_the_separator_a_name_carries_nowhere_joins_the_parts(self) -> None:
        assert identity_digest("folder", "take") == calculate_hash(f"folder{IDENTITY_SEPARATOR}take")

    def test_digest_takes_the_length_it_is_asked_for(self) -> None:
        assert len(identity_digest("take", length=8)) == 8
        assert len(identity_digest("take")) == HASH_LENGTH

    def test_a_shorter_digest_opens_the_full_one(self) -> None:
        assert identity_digest("take").startswith(identity_digest("take", length=8))
