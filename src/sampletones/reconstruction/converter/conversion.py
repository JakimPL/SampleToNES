import gc
from pathlib import Path
from typing import Tuple

from ...exceptions import UnsupportedAudioFormatError
from ...utils.logger import logger
from ..reconstructor.reconstructor import Reconstructor


def reconstruct_file(arguments: Tuple[Reconstructor, Path, Path]) -> Path:
    reconstructor, input_path, output_path = arguments
    output_path.parent.mkdir(parents=True, exist_ok=True)
    reconstruction = None
    try:
        reconstruction = reconstructor(input_path)
        if reconstruction is not None:
            reconstruction.save(output_path)
        del reconstruction
    except KeyboardInterrupt as exception:
        logger.info("Reconstruction interrupted by user.")
        raise exception
    except UnsupportedAudioFormatError:
        logger.warning(f"Skipping file due to unsupported audio format: {input_path}")
    finally:
        gc.collect()

    return output_path
