from enum import StrEnum
from pathlib import Path
from typing import Final, FrozenSet, Optional, Self, Tuple

from pydantic import BaseModel

from sampletones_application.view_model.shared.nearest import nearest_offered
from sampletones_application.view_model.shared.percent import format_percent
from sampletones_core.audio.writers import (
    DEFAULT_AUDIO_DEPTH,
    MP3_SAMPLE_RATES,
    AudioDepth,
    AudioFormat,
    AudioOutputSpec,
    Mp3OutputSpec,
    WaveOutputSpec,
    capability_of,
    default_mp3_bitrate,
    mp3_bitrates,
)
from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE
from sampletones_core.parallelization import ETAEstimator


class RenderPhase(StrEnum):
    IDLE = "idle"
    CONFIGURING = "configuring"
    RENDERING = "rendering"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


ACTIVE_PHASES: Final[FrozenSet[RenderPhase]] = frozenset(
    {
        RenderPhase.CONFIGURING,
        RenderPhase.RENDERING,
        RenderPhase.CANCELLING,
    }
)


def build_spec(
    audio_format: AudioFormat,
    sample_rate: int,
    *,
    depth: Optional[AudioDepth],
    bitrate: Optional[int],
) -> AudioOutputSpec:
    """The specification a set of standing choices states for ``audio_format``.

    Each choice is snapped onto what the container accepts: the rate becomes the offered one
    nearest it, a depth the format stores is kept, and a bitrate stays where the rate's own
    ladder reaches it. A choice the format leaves behind falls back to what it opens on, so
    moving between containers always arrives at a specification the encoder writes.

    Args:
        audio_format: The container the audio is written into.
        sample_rate: The rate the choices stand at.
        depth: The form each stored sample takes, where one was chosen.
        bitrate: The kilobits each encoded second holds, where one was chosen.

    Returns:
        AudioOutputSpec: The specification for that format.
    """
    match audio_format:
        case AudioFormat.WAVE:
            capability = capability_of(AudioFormat.WAVE)
            return WaveOutputSpec(
                sample_rate=nearest_offered(sample_rate, capability.sample_rates),
                depth=depth if depth is not None and capability.supports_depth(depth) else DEFAULT_AUDIO_DEPTH,
            )
        case AudioFormat.MP3:
            rate = nearest_offered(sample_rate, MP3_SAMPLE_RATES)
            return Mp3OutputSpec(
                sample_rate=rate,
                bitrate=bitrate if bitrate in mp3_bitrates(rate) else default_mp3_bitrate(rate),
            )


class SongRenderSettings(BaseModel, frozen=True):
    """The choices a render is made under: what the file is written as, and at what level.

    Each ``with_`` method answers with the settings carrying one choice changed and the others
    reconciled against what that choice leaves possible, so every value held here is one the
    encoder accepts. The reconciliation runs in one place because the offers depend on each
    other: a container encodes its own set of rates, and each rate offers the bitrates its MPEG
    version defines.
    """

    spec: AudioOutputSpec
    normalize: bool

    @classmethod
    def initial(cls, audio_format: AudioFormat) -> Self:
        """The choices a dialog opens on: ``audio_format`` at the usual rate, rendered at unity."""
        return cls(
            spec=build_spec(
                audio_format,
                DEFAULT_SAMPLE_RATE,
                depth=DEFAULT_AUDIO_DEPTH,
                bitrate=None,
            ),
            normalize=False,
        )

    @property
    def depth(self) -> Optional[AudioDepth]:
        """The form each stored sample takes, where the format stores samples directly."""
        match self.spec:
            case WaveOutputSpec() as wave:
                return wave.depth
            case Mp3OutputSpec():
                return None

    @property
    def bitrate(self) -> Optional[int]:
        """The kilobits each encoded second holds, where the format encodes to a bitrate."""
        match self.spec:
            case WaveOutputSpec():
                return None
            case Mp3OutputSpec() as mp3:
                return mp3.bitrate

    def with_format(self, audio_format: AudioFormat) -> Self:
        """The settings written as ``audio_format``, at the nearest rate it encodes."""
        return self._with_spec(
            build_spec(
                audio_format,
                self.spec.sample_rate,
                depth=self.depth,
                bitrate=self.bitrate,
            )
        )

    def with_sample_rate(self, sample_rate: int) -> Self:
        """The settings written at ``sample_rate``, keeping the quality it reaches there."""
        return self._with_spec(
            build_spec(
                self.spec.audio_format,
                sample_rate,
                depth=self.depth,
                bitrate=self.bitrate,
            )
        )

    def with_depth(self, depth: AudioDepth) -> Self:
        """The settings storing each sample as ``depth``."""
        return self._with_spec(
            build_spec(
                self.spec.audio_format,
                self.spec.sample_rate,
                depth=depth,
                bitrate=self.bitrate,
            )
        )

    def with_bitrate(self, bitrate: int) -> Self:
        """The settings encoding each second to ``bitrate`` kilobits."""
        return self._with_spec(
            build_spec(
                self.spec.audio_format,
                self.spec.sample_rate,
                depth=self.depth,
                bitrate=bitrate,
            )
        )

    def with_normalize(self, normalize: bool) -> Self:
        """The settings scaled so the loudest sample reaches full scale, or left at unity."""
        return self.model_copy(update={"normalize": normalize})

    def _with_spec(self, spec: AudioOutputSpec) -> Self:
        return self.model_copy(update={"spec": spec})


class SongRenderViewModel(BaseModel, frozen=True):
    """What the render dialog draws: the options this installation offers, the choices standing,
    and how far a running render has got.

    The setup and the progress are two faces of one dialog, so the phase decides which is shown
    and the derived flags are read rather than stored. The offers narrow with the choices — the
    rates a container encodes, the bitrates a rate reaches — so a combo repopulates from here as
    soon as the choice above it changes.

    Attributes:
        phase: Where the render stands, from the dialog opening to the outcome it reports.
        formats: The containers this installation writes, in the order they are offered.
        depths: The forms this installation stores the chosen container's samples in.
        settings: The choices the dialog is standing at.
        destination: The file a render writes.
        total_samples: The samples the whole song holds at the chosen rate.
        status_text: What the running pass is doing, and how long it has left.
        progress: How far the running pass has got, from 0 to 1.
    """

    phase: RenderPhase
    formats: Tuple[AudioFormat, ...]
    depths: Tuple[AudioDepth, ...]
    settings: SongRenderSettings
    destination: Path
    total_samples: int
    status_text: str
    progress: float

    @property
    def spec(self) -> AudioOutputSpec:
        return self.settings.spec

    @property
    def sample_rates(self) -> Tuple[int, ...]:
        """The rates the chosen container encodes, lowest first."""
        return self.spec.capability.sample_rates

    @property
    def bitrates(self) -> Tuple[int, ...]:
        """The bitrates the chosen rate encodes at, for a container that offers a bitrate."""
        if self.spec.capability.stores_samples:
            return ()

        return mp3_bitrates(self.spec.sample_rate)

    @property
    def stores_samples(self) -> bool:
        """Whether the chosen container stores samples, which is what gives it a depth to choose."""
        return self.spec.capability.stores_samples

    @property
    def duration_seconds(self) -> float:
        """How long the song plays for, in seconds."""
        return self.total_samples / self.spec.sample_rate

    @property
    def duration_label(self) -> str:
        """The length the render is projected to run to, as the dialog states it."""
        return ETAEstimator.format_duration(self.duration_seconds)

    @property
    def progress_overlay(self) -> str:
        """The percentage label rendered over the progress bar, derived from the fraction."""
        return format_percent(self.progress)

    @property
    def is_active(self) -> bool:
        return self.phase in ACTIVE_PHASES

    @property
    def setup_visible(self) -> bool:
        return self.phase == RenderPhase.CONFIGURING

    @property
    def progress_visible(self) -> bool:
        return self.phase != RenderPhase.CONFIGURING

    @property
    def render_enabled(self) -> bool:
        """Whether a render starts from here: a song with something to write, still being set up."""
        return self.phase == RenderPhase.CONFIGURING and self.total_samples > 0

    @property
    def cancel_enabled(self) -> bool:
        """Whether a running render still takes a stop, which one already stopping has taken."""
        return self.phase == RenderPhase.RENDERING
