import gc
from pathlib import Path
from typing import Tuple

from sampletones_shared.logger import logger

from ..progress import ReconstructionReporter
from ..reconstructor.reconstructor import Reconstructor
from .job import ConversionJob


def reconstruct_job(arguments: Tuple[Reconstructor, ConversionJob, ReconstructionReporter]) -> Path:
    """Builds one job's reconstruction and writes it where the job says.

    Runs in a pool worker, so the job travels with the reconstructor that builds it and the
    reporter it tells its progress to. An error the job meets ends the job, and the run decides
    whether the jobs around it go on.

    Returns:
        The file the job named, whether or not a reconstruction reached it.

    Raises:
        KeyboardInterrupt: If the run is interrupted, so the pool stops.
        OperationCanceled: If the run is withdrawn while the job is under way.
    """
    reconstructor, job, report = arguments
    job.output_path.parent.mkdir(parents=True, exist_ok=True)
    reconstruction = None
    try:
        reconstruction = reconstructor.reconstruct(job.sources, job.stems, report=report)
        if reconstruction is not None:
            reconstruction.save(job.output_path)
        del reconstruction
    except KeyboardInterrupt:
        logger.info("Reconstruction interrupted by user.")
        raise
    finally:
        gc.collect()

    return job.output_path
