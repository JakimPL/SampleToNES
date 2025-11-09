import gc
from pathlib import Path
from typing import List

from configs.config import Config
from constants.browser import EXT_FILE_JSON
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


def get_relative_path(base_directory: Path, wav_file: Path, output_path, suffix: str = EXT_FILE_JSON) -> Path:
    relative_path = wav_file.relative_to(base_directory)
    output_path = output_path / relative_path
    output_path = output_path.with_suffix(EXT_FILE_JSON)
    return output_path


def get_output_directory(config: Config) -> Path:
    config_directory = generate_config_directory_name(config)
    output_directory = Path(config.general.output_directory) / config_directory
    return output_directory


def filter_files(
    wav_files: List[Path],
    base_directory: Path,
    output_directory: Path,
) -> List[Path]:
    filtered_files = []
    for wav_file in wav_files:
        output_path = get_relative_path(base_directory, wav_file, output_directory)
        if not output_path.exists():
            filtered_files.append(wav_file)

    return filtered_files


def reconstruct_file(reconstructor: Reconstructor, input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    reconstruction = reconstructor(input_path)
    reconstruction.save(output_path)
    gc.collect()
