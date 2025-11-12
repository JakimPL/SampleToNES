import gc
from pathlib import Path
from typing import Tuple

from ...utils.logger import logger
from ..reconstructor import Reconstructor


def reconstruct_file(arguments: Tuple[Reconstructor, Path, Path]) -> Path:
    reconstructor, input_path, output_path = arguments
    output_path.parent.mkdir(parents=True, exist_ok=True)
    reconstruction = None
    try:
        reconstruction = reconstructor(input_path)
    except KeyboardInterrupt as exception:
        logger.info("Reconstruction interrupted by user.")
        raise exception
    except Exception as exception:  # TODO: specify exception type
        logger.error_with_traceback(str(type(exception)), exception)

    if reconstruction is not None:
        reconstruction.save(output_path)

    del reconstruction
    gc.collect()

    return output_path
