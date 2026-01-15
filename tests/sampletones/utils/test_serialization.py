import tempfile
from pathlib import Path
from typing import Dict, List, Union

import numpy as np
import pytest

from sampletones.utils.serialization import (
    calculate_hash,
    deserialize_array,
    dump,
    hash_model,
    hash_models,
    load_binary,
    load_json,
    load_yaml,
    save_binary,
    save_json,
    save_yaml,
    serialize_array,
    snake_to_camel,
)
from tests.sampletones.dummy import NestedModel, SimpleModel


class TestDump:
    def test_dump_dict(self) -> None:
        data = {"key": "value", "number": 42}
        result = dump(data)
        assert result == '{"key":"value","number":42}'
        assert isinstance(result, str)

    def test_dump_list(self) -> None:
        data = [1, 2, 3, "test"]
        result = dump(data)
        assert result == '[1,2,3,"test"]'

    def test_dump_nested_structure(self) -> None:
        data = {"outer": {"inner": [1, 2, 3]}}
        result = dump(data)
        assert result == '{"outer":{"inner":[1,2,3]}}'

    def test_dump_string(self) -> None:
        data = "simple string"
        result = dump(data)
        assert result == '"simple string"'

    def test_dump_number(self) -> None:
        result = dump(123)
        assert result == "123"

    def test_dump_boolean(self) -> None:
        assert dump(True) == "true"
        assert dump(False) == "false"

    def test_dump_null(self) -> None:
        result = dump(None)
        assert result == "null"

    def test_dump_empty_dict(self) -> None:
        result = dump({})
        assert result == "{}"

    def test_dump_empty_list(self) -> None:
        result = dump([])
        assert result == "[]"

    def test_dump_dict_key_order_sorted(self) -> None:
        dict1 = {"a": 1, "b": 2, "c": 3}
        dict2 = {"c": 3, "b": 2, "a": 1}

        result1 = dump(dict1)
        result2 = dump(dict2)

        assert result1 == '{"a":1,"b":2,"c":3}'
        assert result2 == '{"a":1,"b":2,"c":3}'
        assert result1 == result2


class TestJsonFileOperations:
    def test_save_and_load_json_dict(self) -> None:
        data = {"key": "value", "number": 42, "nested": {"inner": [1, 2, 3]}}

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.json"
            save_json(filepath, data)

            assert filepath.exists()

            loaded = load_json(filepath)
            assert loaded == data

    def test_save_and_load_json_list(self) -> None:
        data: List[Union[int, str, Dict[str, str]]] = [1, 2, 3, "test", {"key": "value"}]

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.json"
            save_json(filepath, data)
            loaded = load_json(filepath)
            assert loaded == data

    def test_save_json_with_indentation(self) -> None:
        data = {"key": "value"}

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.json"
            save_json(filepath, data)

            with open(filepath, "r") as f:
                content = f.read()

            assert "\n" in content
            assert "  " in content

    def test_save_json_creates_file(self) -> None:
        data = {"test": 123}

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "new_file.json"
            assert not filepath.exists()

            save_json(filepath, data)
            assert filepath.exists()

    def test_load_json_empty_dict(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.json"
            save_json(filepath, {})
            loaded = load_json(filepath)
            assert loaded == {}

    def test_load_json_with_unicode(self) -> None:
        data = {"message": "Hello 世界 🌍"}

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.json"
            save_json(filepath, data)
            loaded = load_json(filepath)
            assert loaded == data


class TestYamlFileOperations:
    def test_save_and_load_yaml_dict(self) -> None:
        data = {"key": "value", "number": 42, "nested": {"inner": [1, 2, 3]}}

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.yaml"
            save_yaml(filepath, data)

            assert filepath.exists()

            loaded = load_yaml(filepath)
            assert loaded == data

    def test_save_and_load_yaml_list(self) -> None:
        data: List[Union[int, str]] = [1, 2, 3, "test"]

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.yaml"
            save_yaml(filepath, data)
            loaded = load_yaml(filepath)
            assert loaded == data

    def test_save_yaml_creates_file(self) -> None:
        data = {"test": 123}

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "new_file.yaml"
            assert not filepath.exists()

            save_yaml(filepath, data)
            assert filepath.exists()

    def test_load_yaml_empty_dict(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.yaml"
            save_yaml(filepath, {})
            loaded = load_yaml(filepath)
            assert loaded == {}

    def test_yaml_safe_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.yaml"

            with open(filepath, "w") as f:
                f.write("key: value\nnumber: 42")

            loaded = load_yaml(filepath)
            assert loaded == {"key": "value", "number": 42}


class TestBinaryFileOperations:
    def test_save_and_load_binary(self) -> None:
        data = b"binary data \x00\x01\x02\xff"

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.bin"
            save_binary(filepath, data)

            assert filepath.exists()

            loaded = load_binary(filepath)
            assert loaded == data

    def test_save_binary_empty(self) -> None:
        data = b""

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.bin"
            save_binary(filepath, data)
            loaded = load_binary(filepath)
            assert loaded == b""

    def test_save_binary_large(self) -> None:
        data = bytes(range(256)) * 1000

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.bin"
            save_binary(filepath, data)
            loaded = load_binary(filepath)
            assert loaded == data
            assert len(loaded) == 256000

    def test_binary_preserves_exact_bytes(self) -> None:
        data = b"\x00\x01\x7f\x80\xff"

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.bin"
            save_binary(filepath, data)
            loaded = load_binary(filepath)
            assert loaded == data


class TestArraySerialization:
    def test_serialize_deserialize_1d_array(self) -> None:
        array = np.array([1, 2, 3, 4, 5])
        serialized = serialize_array(array)
        deserialized = deserialize_array(serialized)

        np.testing.assert_array_equal(deserialized, array)
        assert deserialized.dtype == array.dtype
        assert deserialized.shape == array.shape

    def test_serialize_deserialize_2d_array(self) -> None:
        array = np.array([[1, 2, 3], [4, 5, 6]])
        serialized = serialize_array(array)
        deserialized = deserialize_array(serialized)

        np.testing.assert_array_equal(deserialized, array)
        assert deserialized.shape == (2, 3)

    def test_serialize_deserialize_float_array(self) -> None:
        array = np.array([1.5, 2.7, 3.14159], dtype=np.float32)
        serialized = serialize_array(array)
        deserialized = deserialize_array(serialized)

        np.testing.assert_array_almost_equal(deserialized, array)
        assert deserialized.dtype == np.float32

    def test_serialize_deserialize_complex_array(self) -> None:
        array = np.array([1 + 2j, 3 + 4j], dtype=np.complex64)
        serialized = serialize_array(array)
        deserialized = deserialize_array(serialized)

        np.testing.assert_array_equal(deserialized, array)
        assert deserialized.dtype == np.complex64

    def test_serialize_array_structure(self) -> None:
        array = np.array([1, 2, 3])
        serialized = serialize_array(array)

        assert "data" in serialized
        assert "shape" in serialized
        assert "dtype" in serialized
        assert isinstance(serialized["data"], str)
        assert serialized["shape"] == (3,)

    def test_serialize_empty_array(self) -> None:
        array = np.array([])
        serialized = serialize_array(array)
        deserialized = deserialize_array(serialized)

        np.testing.assert_array_equal(deserialized, array)
        assert deserialized.shape == (0,)

    def test_serialize_3d_array(self) -> None:
        array = np.arange(24).reshape(2, 3, 4)
        serialized = serialize_array(array)
        deserialized = deserialize_array(serialized)

        np.testing.assert_array_equal(deserialized, array)
        assert deserialized.shape == (2, 3, 4)

    def test_serialize_different_dtypes(self) -> None:
        dtypes = [np.int8, np.int16, np.int32, np.int64, np.uint8, np.float16, np.float32, np.float64]

        for dtype in dtypes:
            array = np.array([1, 2, 3], dtype=dtype)
            serialized = serialize_array(array)
            deserialized = deserialize_array(serialized)

            np.testing.assert_array_equal(deserialized, array)
            assert deserialized.dtype == dtype


class TestCalculateHash:
    def test_hash_string(self) -> None:
        hash1 = calculate_hash("test")
        hash2 = calculate_hash("test")

        assert hash1 == hash2
        assert isinstance(hash1, str)
        assert len(hash1) == 32

    def test_hash_different_strings(self) -> None:
        hash1 = calculate_hash("test1")
        hash2 = calculate_hash("test2")

        assert hash1 != hash2

    def test_hash_integer(self) -> None:
        hash1 = calculate_hash(42)
        hash2 = calculate_hash(42)
        hash3 = calculate_hash(1)

        assert hash1 == hash2
        assert hash1 != hash3
        assert isinstance(hash1, str)

    def test_hash_different_integers(self) -> None:
        hash1 = calculate_hash(1)
        hash2 = calculate_hash(2)

        assert hash1 != hash2

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

    def test_hash_bytes(self) -> None:
        hash1 = calculate_hash(b"\x00\x01\x02\xff")
        hash2 = calculate_hash(b"\x00\x01\x02\xff")

        assert hash1 == hash2
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

    def test_hash_bool_different_representations(self) -> None:
        hash_false = calculate_hash(False)
        hash_zero = calculate_hash(0)
        hash_float_zero = calculate_hash(0.0)
        hash_empty_string = calculate_hash("")
        hash_null_bytes = calculate_hash(b"")
        hash_none = calculate_hash(None)

        assert hash_false == hash_zero
        assert hash_false == hash_float_zero
        assert hash_false == hash_empty_string
        assert hash_false == hash_null_bytes
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

    def test_hash_empty_string(self) -> None:
        hash1 = calculate_hash("")
        hash2 = calculate_hash("")

        assert hash1 == hash2
        assert len(hash1) == 32

    def test_hash_empty_bytes(self) -> None:
        hash1 = calculate_hash(b"")
        hash2 = calculate_hash(b"")

        assert hash1 == hash2

    def test_hash_zero_integer(self) -> None:
        hash1 = calculate_hash(0)
        hash2 = calculate_hash(0)

        assert hash1 == hash2

    def test_hash_zero_float(self) -> None:
        hash1 = calculate_hash(0.0)
        hash2 = calculate_hash(0.0)

        assert hash1 == hash2

    def test_hash_negative_integer(self) -> None:
        hash1 = calculate_hash(-42)
        hash2 = calculate_hash(-42)

        assert hash1 == hash2

    def test_hash_negative_float(self) -> None:
        hash1 = calculate_hash(-3.14)
        hash2 = calculate_hash(-3.14)

        assert hash1 == hash2

    def test_hash_tuple(self) -> None:
        hash1 = calculate_hash((1, 2, 3))
        hash2 = calculate_hash((1, 2, 3))

        assert hash1 == hash2

    def test_hash_frozenset(self) -> None:
        hash1 = calculate_hash(frozenset([1, 2, 3]))
        hash2 = calculate_hash(frozenset([1, 2, 3]))

        assert hash1 == hash2
        assert isinstance(hash1, str)

    def test_hash_frozenset_order_independent(self) -> None:
        hash1 = calculate_hash(frozenset([1, 2, 3]))
        hash2 = calculate_hash(frozenset([3, 2, 1]))

        assert hash1 == hash2


class TestHashModels:
    def test_hash_single_model(self) -> None:
        model = SimpleModel(value=42, name="test")
        hash1 = hash_model(model)
        hash2 = hash_model(model)

        assert hash1 == hash2
        assert isinstance(hash1, str)
        assert len(hash1) == 32

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


class TestSnakeToCamel:
    def test_snake_to_camel_basic(self) -> None:
        assert snake_to_camel("hello_world") == "HelloWorld"

    def test_snake_to_camel_multiple_words(self) -> None:
        assert snake_to_camel("my_variable_name") == "MyVariableName"

    def test_snake_to_camel_single_word(self) -> None:
        assert snake_to_camel("single") == "Single"

    def test_snake_to_camel_two_words(self) -> None:
        assert snake_to_camel("first_second") == "FirstSecond"

    def test_snake_to_camel_with_numbers(self) -> None:
        assert snake_to_camel("test_123_value") == "Test123Value"

    def test_snake_to_camel_empty_string(self) -> None:
        assert snake_to_camel("") == ""

    def test_snake_to_camel_no_underscores(self) -> None:
        assert snake_to_camel("nounderscores") == "Nounderscores"

    def test_snake_to_camel_trailing_underscore(self) -> None:
        result = snake_to_camel("trailing_")
        assert result == "Trailing"

    def test_snake_to_camel_leading_underscore(self) -> None:
        result = snake_to_camel("_leading")
        assert result == "Leading"

    def test_snake_to_camel_double_underscore(self) -> None:
        result = snake_to_camel("double__underscore")
        assert result == "DoubleUnderscore"

    def test_snake_to_camel_lowercase_preserved(self) -> None:
        assert snake_to_camel("lower_case") == "LowerCase"

    def test_snake_to_camel_already_capitalized(self) -> None:
        assert snake_to_camel("Already_Capitalized") == "AlreadyCapitalized"


class TestEdgeCases:
    def test_dump_non_serializable_raises(self) -> None:
        with pytest.raises(TypeError):
            dump(object())

    def test_calculate_hash_list_raises(self) -> None:
        with pytest.raises(TypeError):
            calculate_hash([1, 2, 3])  # type: ignore

    def test_calculate_hash_dict_raises(self) -> None:
        with pytest.raises(TypeError):
            calculate_hash({"key": "value"})  # type: ignore

    def test_save_json_nested_complex(self) -> None:
        data = {"level1": {"level2": {"level3": [1, 2, {"level4": "deep"}]}}}

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "complex.json"
            save_json(filepath, data)
            loaded = load_json(filepath)
            assert loaded == data

    def test_array_roundtrip_preserves_values(self) -> None:
        original = np.random.rand(10, 10)
        serialized = serialize_array(original)
        restored = deserialize_array(serialized)

        np.testing.assert_array_almost_equal(restored, original)
