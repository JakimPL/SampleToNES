import gc
from pathlib import Path
from typing import Tuple

from ..reconstructor import Reconstructor


def reconstruct_file(arguments: Tuple[Reconstructor, Path, Path]) -> Path:
    reconstructor, input_path, output_path = arguments
    output_path.parent.mkdir(parents=True, exist_ok=True)
    reconstruction = reconstructor(input_path)
    if reconstruction is not None:
        reconstruction.save(output_path)

    gc.collect()
    return output_path
