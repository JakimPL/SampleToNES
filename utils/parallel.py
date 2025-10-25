from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import Callable, List, Optional, Tuple, Type, TypeVar, Union

T = TypeVar("T")
R = TypeVar("R")
ExecutorType = Union[Type[ThreadPoolExecutor], Type[ProcessPoolExecutor]]


def parallelize(
    function: Callable[..., R],
    collection: List[T],
    *args,
    executor: ExecutorType = ProcessPoolExecutor,
    max_workers: Optional[int] = None,
    **kwargs,
) -> List[Tuple[int, R]]:
    if not collection:
        return []

    if max_workers is None:
        max_workers = 6

    workers = min(max_workers, len(collection))
    chunks = [list(range(i, len(collection), workers)) for i in range(workers)]

    results = []
    with executor(max_workers=max_workers) as executor:
        future_to_index = {executor.submit(function, chunk, *args, **kwargs): i for i, chunk in enumerate(chunks)}
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as exception:  # TODO: to narrow
                print(f"Task {index} generated an exception: {exception}")
                raise

    return results
