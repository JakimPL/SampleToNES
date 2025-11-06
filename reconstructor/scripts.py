import gc
from pathlib import Path
from typing import List, Union

from tqdm.auto import tqdm

from configs import config
from configs.config import Config
from constants.browser import EXT_FILE_JSON, EXT_FILE_WAV
from constants.enums import GENERATOR_ABBREVIATIONS, GeneratorName
from reconstructor.reconstructor import Reconstructor
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


def reconstruct_directory(config: Config, directory: Union[str, Path]) -> None:
    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"Directory does not exist: {directory}")

    if not directory.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {directory}")

    try:
        config_directory = generate_config_directory_name(config)
        output_path = Path(config.general.output_directory) / config_directory / directory.name
        wav_files = list(directory.rglob(f"*{EXT_FILE_WAV}"))
        reconstructor = Reconstructor(config)
        for wav_file in tqdm(wav_files, desc="WAV files", leave=False):
            relative_path = wav_file.relative_to(directory)
            output_path = output_path / relative_path

        del reconstructor
    finally:
        gc.collect()
