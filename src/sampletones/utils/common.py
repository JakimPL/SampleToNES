from typing import Any, Dict


def next_power_of_two(length: int) -> int:
    """
    Calculates the next power of two greater than or equal to the given length.

    Args:
        length: The input value.

    Returns:
        The smallest power of two that is greater than or equal to length.

    Raises:
        ValueError: If length is negative.
        OverflowError: If length is too large to compute the next power of two.

    Examples:
        >>> next_power_of_two(0)
        1
        >>> next_power_of_two(5)
        8
        >>> next_power_of_two(8)
        8
        >>> next_power_of_two(17)
        32
    """
    if length < 0:
        raise ValueError("Length must be a positive integer")

    if length == 0:
        return 1

    if length > (1 << 63):
        raise OverflowError("Length is too large to compute the next power of two")

    return 1 << (length - 1).bit_length()


def first_key_for_value(dictionary: Dict[Any, Any], target: Any) -> Any:
    """
    Finds the first key in a dictionary that maps to the specified value.

    Respects the insertion order of keys in the dictionary.

    Args:
        dictionary: The dictionary to search.
        target: The value to search for.

    Returns:
        The first key that maps to the target value, or None if not found.

    Examples:
        >>> first_key_for_value({'a': 1, 'b': 2, 'c': 1}, 2)
        'b'
        >>> first_key_for_value({'c': 1, 'b': 2, 'a': 1}, 1)
        'c'
        >>> first_key_for_value({'a': 1, 'b': 2}, 3)  # returns None

    """
    if not isinstance(dictionary, dict):
        raise TypeError(f"Expected dictionary to be dict, got {type(dictionary)}")

    for key, value in dictionary.items():
        if value == target:
            return key

    return None
