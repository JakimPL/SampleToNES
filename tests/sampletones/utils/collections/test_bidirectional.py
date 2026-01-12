import pytest

from sampletones.utils.collections.bidirectional import BidirectionalHashMap


def test_bidirectional_hash_map_invalid_input():
    bidirectional = BidirectionalHashMap()
    with pytest.raises(TypeError):
        bidirectional[0] = 0

    with pytest.raises(TypeError):
        bidirectional["a"] = "a"


def test_bidirectional_hash_map_conflict():
    bidirectional = BidirectionalHashMap()
    bidirectional["1"] = 2
    bidirectional["1"] = 3
    bidirectional["2"] = 2
    with pytest.raises(ValueError):
        bidirectional["2"] = 2
