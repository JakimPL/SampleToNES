import gc
from multiprocessing import Manager
from pathlib import Path
from typing import Any, List, Optional, Union

from configs.config import Config
from constants.browser import EXT_FILE_JSON, EXT_FILE_WAV
from constants.enums import GENERATOR_ABBREVIATIONS, GeneratorName
from reconstructor.reconstructor import Reconstructor
from utils.parallelization.parallel import parallelize
from utils.serialization import hash_models


def abbreviate_generator_names(generator_names: List[GeneratorName]) -> str:
    return "".join(GENERATOR_ABBREVIATIONS[name] for name in generator_names)


def generate_config_directory_name(config: Config) -> str:
    sample_rate = config.library.sample_rate
    change_rate = config.library.change_rate
    generators = abbreviate_generator_names(config.generation.generators)
    config_hash = hash_models(config.library, config.generation)
    config_directory = f"{sample_rate}_{change_rate}_{generators}_{config_hash}"
    return config_directory


def reconstruct_file(reconstructor: Reconstructor, input_path: Path, output_path: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")

    if not input_path.is_file():
        raise IsADirectoryError(f"Input path is not a file: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path = output_path.with_suffix(EXT_FILE_JSON)

    # TODO: ask for skip/replace
    if output_path.exists():
        return

    reconstruction = reconstructor(input_path)
    reconstruction.save(output_path)
    gc.collect()


def reconstruct_single_file(
    config: Config,
    input_path: Union[str, Path],
    progress_queue: Optional[Any] = None,
    cancel_flag: Optional[Any] = None,
) -> Path:
    input_path = Path(input_path)
    config_directory = generate_config_directory_name(config)
    output_directory = Path(config.general.output_directory) / config_directory
    output_path = output_directory / input_path.stem

    try:
        reconstructor = Reconstructor(config)
        reconstruct_file(reconstructor, input_path, output_path)

        if progress_queue:
            progress_queue.put(("completed", str(input_path)))

        del reconstructor
    finally:
        gc.collect()

    return output_path.with_suffix(EXT_FILE_JSON)


def reconstruct_directory_file(
    file_ids: List[int],
    wav_files: List[Path],
    reconstructor: Reconstructor,
    directory: Path,
    output_directory: Path,
    progress_queue: Optional[Any] = None,
    cancel_flag: Optional[Any] = None,
) -> None:
    for idx in file_ids:
        if cancel_flag and cancel_flag.value:
            return

        wav_file = wav_files[idx]
        relative_path = wav_file.relative_to(directory)
        output_path = output_directory / relative_path
        reconstruct_file(reconstructor, wav_file, output_path)

        if progress_queue:
            progress_queue.put(("completed", str(wav_file)))


def reconstruct_directory(
    config: Config, directory: Union[str, Path], progress_queue: Optional[Any] = None, cancel_flag: Optional[Any] = None
) -> None:
    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"Directory does not exist: {directory}")

    if not directory.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {directory}")

    try:
        config_directory = generate_config_directory_name(config)
        output_directory = Path(config.general.output_directory) / config_directory / directory.name
        wav_files = list(directory.rglob(f"*{EXT_FILE_WAV}"))

        if not wav_files:
            raise ValueError(f"No WAV files found in directory: {directory}")

        if progress_queue:
            progress_queue.put(("total", len(wav_files)))

        reconstructor = Reconstructor(config)
        file_ids = list(range(len(wav_files)))
        parallelize(
            reconstruct_directory_file,
            file_ids,
            wav_files=wav_files,
            max_workers=config.general.max_workers,
            reconstructor=reconstructor,
            directory=directory,
            output_directory=output_directory,
            progress_queue=progress_queue,
            cancel_flag=cancel_flag,
        )

        del reconstructor
    finally:
        gc.collect()
