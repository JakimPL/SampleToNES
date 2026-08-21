import gc
from pathlib import Path
from typing import Tuple

from sampletones_shared.exceptions import UnsupportedAudioFormatError
from sampletones_shared.logger import logger

from ..reconstructor.reconstructor import Reconstructor
from .job import ConversionJob


def reconstruct_job(arguments: Tuple[Reconstructor, ConversionJob]) -> Path:
    """Builds one job's reconstruction and writes it where the job says.

    Runs in a pool worker, so the job travels with the reconstructor that builds it. A source
    in a format the loader has no reader for is reported and left, which keeps one such file
    from ending a batch.

    Returns:
        The file the job named, whether or not a reconstruction reached it.

    Raises:
        KeyboardInterrupt: If the run is interrupted, so the pool stops.
    """
    reconstructor, job = arguments
    job.output_path.parent.mkdir(parents=True, exist_ok=True)
    reconstruction = None
    try:
        reconstruction = reconstructor.reconstruct(job.sources, job.stems)
        if reconstruction is not None:
            reconstruction.save(job.output_path)
        del reconstruction
    except KeyboardInterrupt:
        logger.info("Reconstruction interrupted by user.")
        raise
    except UnsupportedAudioFormatError:
        logger.warning(f"Skipping job due to unsupported audio format: {job.sources}")
    finally:
        gc.collect()

    return job.output_path
