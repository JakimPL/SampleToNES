from typing import List

from sampletones_core.configs import Config
from sampletones_core.exporters.maps import CHANNEL_TO_EXPORTER_MAP
from sampletones_tools.calibration.config.chords import ChordsConfig

from .families import Family
from .item import CorpusItem
from .nes import held, written_item


def build_chords(config: Config, *, corpus: ChordsConfig) -> List[CorpusItem]:
    """Every chord: its channels held together on their frames, then silent.

    Args:
        config: The configuration the chords are rendered at, the one the run converts with.
        corpus: The chords and the length they hold for.

    Returns:
        List[CorpusItem]: One item per chord, in the order the corpus lists them.

    Raises:
        ValidationError: If a chord's frame is no instruction its channel takes.
    """
    return [
        written_item(
            chord.name,
            Family.CHORDS,
            chord.category,
            listed=chord.listed,
            instructions={
                channel: held(
                    channel,
                    CHANNEL_TO_EXPORTER_MAP[channel].get_instruction_type().model_validate(frame),
                    sounding=corpus.sounding_frames,
                    silent=corpus.silent_frames,
                )
                for channel, frame in chord.frames.items()
            },
            config=config,
        )
        for chord in corpus.chords
    ]
