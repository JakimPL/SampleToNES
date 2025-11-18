from pathlib import Path
from typing import List

from sampletones.configs import Config
from sampletones.constants.enums import GENERATOR_ABBREVIATIONS, GeneratorName
from sampletones.constants.paths import EXT_FILE_RECONSTRUCTION
from sampletones.utils import hash_models


def abbreviate_generator_names(generator_names: List[GeneratorName]) -> str:
    return "".join(GENERATOR_ABBREVIATIONS[name] for name in generator_names)


def generate_config_directory_name(config: Config) -> str:
    sample_rate = config.library.sample_rate
    change_rate = config.library.change_rate
    generators = abbreviate_generator_names(config.generation.generators)
    config_hash = hash_models(config.library, config.generation)
    config_directory = f"{sample_rate}_{change_rate}_{generators}_{config_hash}"
    return config_directory


def get_relative_path(
    base_directory: Path,
    wav_file: Path,
    output_path: Path,
    suffix: str = EXT_FILE_RECONSTRUCTION,
) -> Path:
    relative_path = wav_file.relative_to(base_directory)
    output_path = output_path / relative_path
    output_path = output_path.with_suffix(suffix)
    return Path(output_path.absolute())


def get_output_path(config: Config, input_path: Path, suffix: str = EXT_FILE_RECONSTRUCTION) -> Path:
    config_directory = generate_config_directory_name(config)
    output_directory = Path(config.general.output_directory) / config_directory
    if input_path.is_dir():
        return output_directory / input_path.name
    if input_path.is_file():
        return output_directory / input_path.with_suffix(suffix).name
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")

    raise OSError(f"Invalid path: {input_path}")


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
