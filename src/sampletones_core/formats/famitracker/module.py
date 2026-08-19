from typing import Sequence

from sampletones_core.formats.famitracker.binary import FamiTrackerWriter
from sampletones_core.formats.famitracker.model.instrument import Instrument2A03
from sampletones_core.formats.famitracker.model.module import (
    FamiTrackerModule,
    ModuleInformation,
    ModuleParameters,
    Track,
)
from sampletones_core.formats.famitracker.model.pattern import PatternData
from sampletones_core.formats.famitracker.sequences.pooled import PooledSequence
from sampletones_core.formats.famitracker.sequences.pooling import (
    SequenceReferences,
    build_sequence_pool,
)
from sampletones_core.formats.famitracker.specification.blocks import (
    BLOCK_COMMENTS,
    BLOCK_DPCM_SAMPLES,
    BLOCK_FRAMES,
    BLOCK_HEADER,
    BLOCK_INFO,
    BLOCK_INSTRUMENTS,
    BLOCK_PARAMS,
    BLOCK_PATTERNS,
    BLOCK_SEQUENCES,
)
from sampletones_core.formats.famitracker.specification.channels import ChannelId
from sampletones_core.formats.famitracker.specification.file import (
    FTM_END_MARKER,
    FTM_MAGIC,
    FTM_VERSION,
    INFO_STRING_LENGTH,
)
from sampletones_core.formats.famitracker.specification.instruments import (
    DPCM_KEY_ASSIGNMENTS,
    DPCM_KEY_BYTES,
    EMPTY_DPCM_SAMPLES,
    INSTRUMENT_TYPE_2A03,
)
from sampletones_core.formats.famitracker.specification.parameters import (
    COMMENT_HIDDEN_ON_OPEN,
    FIRST_TRACK_INDEX,
    SINGLE_TRACK_COUNT,
)
from sampletones_core.formats.famitracker.specification.sequences import (
    SEQUENCE_COUNT_2A03,
    SEQUENCE_DISABLED,
    SEQUENCE_ENABLED,
    SequenceKind,
)


def _write_file_header(writer: FamiTrackerWriter) -> None:
    writer.write_bytes(FTM_MAGIC)
    writer.write_uint32(FTM_VERSION)


def _write_params_block(writer: FamiTrackerWriter, parameters: ModuleParameters) -> None:
    with writer.block(BLOCK_PARAMS) as body:
        body.write_uint8(parameters.expansion_chip)
        body.write_int32(parameters.channel_count)
        body.write_int32(int(parameters.machine))
        body.write_int32(parameters.engine_speed)
        body.write_int32(parameters.vibrato_style)
        body.write_int32(parameters.highlight_first)
        body.write_int32(parameters.highlight_second)
        body.write_int32(parameters.speed_split_point)


def _write_info_block(writer: FamiTrackerWriter, information: ModuleInformation) -> None:
    with writer.block(BLOCK_INFO) as body:
        body.write_fixed_string(information.title, INFO_STRING_LENGTH)
        body.write_fixed_string(information.author, INFO_STRING_LENGTH)
        body.write_fixed_string(information.copyright, INFO_STRING_LENGTH)


def _write_header_block(writer: FamiTrackerWriter, track: Track) -> None:
    with writer.block(BLOCK_HEADER) as body:
        body.write_uint8(SINGLE_TRACK_COUNT - 1)
        body.write_terminated_string(track.title)
        for channel_id in ChannelId:
            body.write_uint8(int(channel_id))
            body.write_uint8(track.effect_columns[channel_id] - 1)


def _write_instrument_body(
    writer: FamiTrackerWriter,
    instrument: Instrument2A03,
    references: SequenceReferences,
) -> None:
    writer.write_int32(SEQUENCE_COUNT_2A03)
    for kind in SequenceKind:
        enabled = instrument.sequences[kind].enabled
        writer.write_uint8(SEQUENCE_ENABLED if enabled else SEQUENCE_DISABLED)
        writer.write_uint8(references.get((instrument.index, kind), 0))

    writer.write_bytes(bytes(DPCM_KEY_ASSIGNMENTS * DPCM_KEY_BYTES))


def _write_instruments_block(
    writer: FamiTrackerWriter,
    instruments: Sequence[Instrument2A03],
    references: SequenceReferences,
) -> None:
    with writer.block(BLOCK_INSTRUMENTS) as body:
        body.write_int32(len(instruments))
        for instrument in instruments:
            body.write_int32(instrument.index)
            body.write_uint8(INSTRUMENT_TYPE_2A03)
            _write_instrument_body(body, instrument, references)
            body.write_counted_string(instrument.name)


def _write_sequences_block(writer: FamiTrackerWriter, pool: Sequence[PooledSequence]) -> None:
    with writer.block(BLOCK_SEQUENCES) as body:
        body.write_int32(len(pool))
        for pooled in pool:
            body.write_int32(pooled.index)
            body.write_int32(int(pooled.kind))
            body.write_uint8(len(pooled.sequence.items))
            body.write_int32(pooled.sequence.loop_point)
            for item in pooled.sequence.items:
                body.write_int8(item)
        for pooled in pool:
            body.write_int32(pooled.sequence.release_point)
            body.write_int32(pooled.sequence.setting)


def _write_frames_block(writer: FamiTrackerWriter, track: Track) -> None:
    with writer.block(BLOCK_FRAMES) as body:
        body.write_int32(len(track.order))
        body.write_int32(track.speed)
        body.write_int32(track.tempo)
        body.write_int32(track.rows_per_pattern)
        for frame in track.order:
            for pattern_index in frame:
                body.write_uint8(pattern_index)


def _write_patterns_block(writer: FamiTrackerWriter, patterns: Sequence[PatternData]) -> None:
    with writer.block(BLOCK_PATTERNS) as body:
        for pattern in patterns:
            body.write_int32(FIRST_TRACK_INDEX)
            body.write_int32(int(pattern.channel))
            body.write_int32(pattern.index)
            body.write_int32(len(pattern.rows))
            for row in pattern.rows:
                body.write_int32(row.row_number)
                body.write_int8(row.note)
                body.write_int8(row.octave)
                body.write_int8(row.instrument)
                body.write_int8(row.volume)
                for effect, param in row.effects:
                    body.write_int8(effect)
                    body.write_int8(param)


def _write_dpcm_samples_block(writer: FamiTrackerWriter) -> None:
    with writer.block(BLOCK_DPCM_SAMPLES) as body:
        body.write_uint8(EMPTY_DPCM_SAMPLES)


def _write_comments_block(writer: FamiTrackerWriter, comment: str) -> None:
    with writer.block(BLOCK_COMMENTS) as body:
        body.write_int32(COMMENT_HIDDEN_ON_OPEN)
        body.write_terminated_string(comment)


def module_to_ftm_bytes(module: FamiTrackerModule) -> bytes:
    """Serializes a FamiTracker module to the ``.ftm`` byte layout."""
    pool, references = build_sequence_pool(module.instruments)

    writer = FamiTrackerWriter()
    _write_file_header(writer)
    _write_params_block(writer, module.parameters)
    _write_info_block(writer, module.information)
    _write_header_block(writer, module.track)
    _write_instruments_block(writer, module.instruments, references)
    _write_sequences_block(writer, pool)
    _write_frames_block(writer, module.track)
    _write_patterns_block(writer, module.track.patterns)
    _write_dpcm_samples_block(writer)
    _write_comments_block(writer, module.comment)
    writer.write_bytes(FTM_END_MARKER)
    return writer.data
