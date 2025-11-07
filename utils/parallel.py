from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import (
    Any,
    Callable,
    Concatenate,
    List,
    Optional,
    ParamSpec,
    Type,
    TypeVar,
    Union,
)

from constants.general import MAX_WORKERS

P = ParamSpec("P")
R = TypeVar("R")
ExecutorType = Type[Union[ThreadPoolExecutor, ProcessPoolExecutor]]


def parallelize(
    function: Callable[Concatenate[List[int], P], R],
    collection: List[int],
    *args,
    executor_class: ExecutorType = ProcessPoolExecutor,
    max_workers: Optional[int] = None,
    **kwargs,
) -> List[Any]:
    if not collection:
        return []

    if max_workers is None:
        max_workers = MAX_WORKERS

    workers = min(max_workers, len(collection))
    chunks = [list(range(i, len(collection), workers)) for i in range(workers)]

    results = []
    with executor_class(max_workers=max_workers) as executor:
        future_to_index = {executor.submit(function, chunk, *args, **kwargs): i for i, chunk in enumerate(chunks)}
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                result = future.result()
                results.append(result)
            except KeyboardInterrupt:
                print("Parallel execution interrupted by user.")
                executor.shutdown(wait=False, cancel_futures=True)
                raise
            except Exception as exception:  # TODO: to narrow
                print(f"Task {index} generated an exception: {exception}")
                raise exception

    return results
