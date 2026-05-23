from pathlib import Path
from typing import List, Tuple

from sampletones.configs import Config
from sampletones.constants.enums import GENERATOR_ABBREVIATIONS, GeneratorName
from sampletones.constants.paths import EXT_FILE_RECONSTRUCTION, EXT_FILES_AUDIO
from sampletones_shared.utils.serialization import hash_models
from sampletones_shared.utils.system.paths import to_path


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
    audio_file: Path,
    output_path: Path,
    suffix: str = EXT_FILE_RECONSTRUCTION,
) -> Path:
    relative_path = audio_file.relative_to(base_directory)
    output_path = output_path / relative_path
    output_path = output_path.with_suffix(suffix)
    return Path(output_path.absolute())


def get_output_path(config: Config, input_path: Path, suffix: str = EXT_FILE_RECONSTRUCTION) -> Path:
    config_directory = generate_config_directory_name(config)
    output_directory = to_path(config.general.output_directory) / config_directory
    if input_path.is_dir():
        return output_directory / input_path.name
    if input_path.is_file():
        return output_directory / input_path.with_suffix(suffix).name
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")

    raise OSError(f"Invalid path: {input_path}")


def get_audio_files(
    input_directory: Path,
    extensions: Tuple[str, ...] = EXT_FILES_AUDIO,
    sort: bool = False,
) -> List[Path]:
    audio_files = [path for path in input_directory.rglob("*") if path.is_file() and path.suffix.lower() in extensions]
    if sort:
        audio_files.sort()

    return audio_files


def filter_files(
    audio_files: List[Path],
    base_directory: Path,
    output_directory: Path,
) -> List[Path]:
    filtered_files = []
    for audio_file in audio_files:
        output_path = get_relative_path(base_directory, audio_file, output_directory)
        if not output_path.exists():
            filtered_files.append(audio_file)

    return filtered_files
