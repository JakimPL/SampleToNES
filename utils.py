import base64
import json
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar, Union

import numpy as np

T = TypeVar("T")
R = TypeVar("R")
ExecutorType = Union[Type[ThreadPoolExecutor], Type[ProcessPoolExecutor]]


def next_power_of_two(length: int) -> int:
    return 1 << (length - 1).bit_length()


def pad(audio: np.ndarray, left: int, right: int) -> np.ndarray:
    n = len(audio)
    length = right - left
    output = np.zeros(length, dtype=audio.dtype)

    valid_left = max(left, 0)
    valid_right = min(right, n)

    insert_left = valid_left - left
    insert_right = insert_left + (valid_right - valid_left)

    if valid_right > valid_left:
        output[insert_left:insert_right] = audio[valid_left:valid_right]

    return output


def dump(dictionary: Dict[str, Any]) -> str:
    return json.dumps(dictionary, separators=(",", ":"))


def first_key_for_value(dictionary: dict, target: Any) -> Any:
    for key, value in dictionary.items():
        if value == target:
            return key

    return None


def serialize_array(array: np.ndarray) -> Dict[str, Any]:
    return {
        "data": base64.b64encode(array.tobytes()).decode("utf-8"),
        "shape": array.shape,
        "dtype": str(array.dtype),
    }


def deserialize_array(data: Dict[str, Any]) -> np.ndarray:
    array_data = base64.b64decode(data["data"].encode("utf-8"))
    array = np.frombuffer(array_data, dtype=data["dtype"])
    return array.reshape(data["shape"])


def parallelize(
    collection: List[T],
    function: Callable[..., R],
    *args,
    executor: ExecutorType = ProcessPoolExecutor,
    max_workers: Optional[int] = None,
    **kwargs,
) -> List[Tuple[int, R]]:
    if not collection:
        return []

    if max_workers is None:
        max_workers = 6

    results = []
    with executor(max_workers=max_workers) as executor:
        future_to_index = {executor.submit(function, item, *args, **kwargs): i for i, item in enumerate(collection)}
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                result = future.result()
                results.append((index, result))
            except Exception as exception:
                print(f"Task {index} generated an exception: {exception}")
                raise

    return results
