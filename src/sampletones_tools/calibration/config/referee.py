from typing import Self, Tuple

from pydantic import BaseModel, Field, NonNegativeInt, PositiveInt

from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.calibration.paths import REFEREE_CONFIG_PATH


class RefereeConfig(BaseModel, frozen=True):
    """
    Tuning of the built-in referees: the band analysis the audio referees share, the frames and bands
    the contour referee reads, and the tolerance and the misplaced-note weight the transcription reads frames with.

    Values are loaded from the packaged `calibration/referee.yaml`, so referee
    scores stay comparable across calibration runs while remaining adjustable
    in one place.
    """

    window_sizes: Tuple[PositiveInt, ...] = Field(
        min_length=1,
        description="STFT window sizes covering the time-frequency trade-off.",
    )
    hop_divisor: PositiveInt = Field(
        description="Window size divided by this gives the STFT hop.",
    )
    band_count: PositiveInt = Field(
        description="Number of ERB-spaced aggregation bands.",
    )
    low_frequency: float = Field(
        gt=0.0,
        description="Lower bound of the band axis in Hz.",
    )
    energy_floor: float = Field(
        gt=0.0,
        description="Absolute floor keeping silent band energies finite.",
    )
    audibility_range_decibels: float = Field(
        gt=0.0,
        description="Audible range below the reference's loudest band; quieter content saturates.",
    )
    compression_exponent: float = Field(
        gt=0.0,
        le=1.0,
        description="Exponent turning a band's energy relative to the loudest into its specific loudness.",
    )
    dynamic_range_decibels: float = Field(
        gt=0.0,
        description="Range below the reference's loudest band the loudness-weighted referee reads.",
    )
    level_matching: bool = Field(
        description="Whether the loudness-weighted referee matches the estimate's level before comparing shapes.",
    )
    contour_frame_rate: PositiveInt = Field(
        description="Frames per second the contour referee measures levels over.",
    )
    contour_audible_decibels: float = Field(
        gt=0.0,
        description="Range below the recording's loudest frame the contour referee reads.",
    )
    contour_onset_frames: PositiveInt = Field(
        description="The most frames at the start of each audible run the contour referee reads an onset over.",
    )
    contour_band_centers: Tuple[float, ...] = Field(
        min_length=1,
        description="Centers in Hz of the octave bands the contour referee balances.",
    )
    contour_band_floor_decibels: float = Field(
        gt=0.0,
        description="Range below the recording's fullest band the contour referee reads a band within.",
    )
    volume_tolerance: NonNegativeInt = Field(
        description="Volume steps a conversion's frame may stand off a written frame by and still play it as written.",
    )
    misplaced_weight: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "What a written note played at its pitch on another channel kind weighs, a wrong frame weighing one: "
            "such a note is wrong, though milder than a wrong note."
        ),
    )

    @classmethod
    def load(cls) -> Self:
        """
        Load the packaged referee tuning.

        Returns:
            The referee configuration validated from `sampletones_tools/calibration/config/referee.yaml`.

        Raises:
            TypeError: If the configuration file holds anything other than a mapping.
        """
        return load_yaml_model(REFEREE_CONFIG_PATH, cls)
