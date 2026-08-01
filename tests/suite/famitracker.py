import struct
from dataclasses import dataclass
from typing import Dict, List, Tuple

from sampletones_core.formats.famitracker.specification.blocks import BLOCK_NAME_LENGTH
from sampletones_core.formats.famitracker.specification.file import FTM_END_MARKER, FTM_MAGIC
from sampletones_core.formats.famitracker.specification.instruments import (
    DPCM_KEY_ASSIGNMENTS,
    DPCM_KEY_BYTES,
)
from sampletones_core.formats.famitracker.specification.sequences import SEQUENCE_COUNT_2A03


class _Cursor:
    def __init__(self, data: bytes) -> None:
        self._data = data
        self._offset = 0

    def read(self, count: int) -> bytes:
        chunk = self._data[self._offset : self._offset + count]
        self._offset += count
        return chunk

    def peek(self, count: int) -> bytes:
        return self._data[self._offset : self._offset + count]

    def skip(self, count: int) -> None:
        self._offset += count

    def read_uint8(self) -> int:
        return struct.unpack("<B", self.read(1))[0]

    def read_int8(self) -> int:
        return struct.unpack("<b", self.read(1))[0]

    def read_uint32(self) -> int:
        return struct.unpack("<I", self.read(4))[0]

    def read_int32(self) -> int:
        return struct.unpack("<i", self.read(4))[0]

    def fixed_string(self, length: int) -> str:
        return self.read(length).rstrip(b"\x00").decode("utf-8")

    def counted_string(self) -> str:
        length = self.read_uint32()
        return self.read(length).decode("utf-8")

    def terminated_string(self) -> str:
        start = self._offset
        while self._data[self._offset] != 0:
            self._offset += 1
        text = self._data[start : self._offset].decode("utf-8")
        self._offset += 1
        return text


@dataclass
class ParsedParams:
    expansion_chip: int
    channel_count: int
    machine: int
    engine_speed: int
    vibrato_style: int
    highlight_first: int
    highlight_second: int
    speed_split_point: int


@dataclass
class ParsedInfo:
    title: str
    author: str
    copyright: str


@dataclass
class ParsedChannelHeader:
    channel_id: int
    effect_columns: int


@dataclass
class ParsedHeader:
    track_count: int
    track_titles: List[str]
    channels: List[ParsedChannelHeader]


@dataclass
class ParsedInstrument:
    index: int
    instrument_type: int
    sequence_refs: Dict[int, Tuple[int, int]]
    name: str


@dataclass
class ParsedSequence:
    index: int
    sequence_type: int
    items: List[int]
    loop_point: int
    release_point: int
    setting: int


@dataclass
class ParsedFrames:
    frame_count: int
    speed: int
    tempo: int
    pattern_length: int
    order: List[Tuple[int, ...]]


@dataclass
class ParsedRow:
    row_number: int
    note: int
    octave: int
    instrument: int
    volume: int
    effects: List[Tuple[int, int]]


@dataclass
class ParsedPattern:
    track: int
    channel: int
    index: int
    rows: List[ParsedRow]


@dataclass
class ParsedModule:
    version: int
    params: ParsedParams
    info: ParsedInfo
    header: ParsedHeader
    instruments: List[ParsedInstrument]
    sequences: List[ParsedSequence]
    frames: ParsedFrames
    patterns: List[ParsedPattern]
    dpcm_sample_count: int
    comment: str
    block_versions: Dict[str, int]


def _read_blocks(cursor: _Cursor) -> Tuple[Dict[str, bytes], Dict[str, int]]:
    payloads: Dict[str, bytes] = {}
    versions: Dict[str, int] = {}
    while cursor.peek(len(FTM_END_MARKER)) != FTM_END_MARKER:
        name = cursor.read(BLOCK_NAME_LENGTH).rstrip(b"\x00").decode("ascii")
        version = cursor.read_int32()
        size = cursor.read_int32()
        payloads[name] = cursor.read(size)
        versions[name] = version

    return payloads, versions


def _parse_params(payload: bytes) -> ParsedParams:
    cursor = _Cursor(payload)
    return ParsedParams(
        expansion_chip=cursor.read_uint8(),
        channel_count=cursor.read_int32(),
        machine=cursor.read_int32(),
        engine_speed=cursor.read_int32(),
        vibrato_style=cursor.read_int32(),
        highlight_first=cursor.read_int32(),
        highlight_second=cursor.read_int32(),
        speed_split_point=cursor.read_int32(),
    )


def _parse_info(payload: bytes) -> ParsedInfo:
    cursor = _Cursor(payload)
    return ParsedInfo(
        title=cursor.fixed_string(32),
        author=cursor.fixed_string(32),
        copyright=cursor.fixed_string(32),
    )


def _parse_header(payload: bytes, channel_count: int) -> ParsedHeader:
    cursor = _Cursor(payload)
    track_count = cursor.read_uint8() + 1
    track_titles = [cursor.terminated_string() for _ in range(track_count)]
    channels: List[ParsedChannelHeader] = []
    for _ in range(channel_count):
        channel_id = cursor.read_uint8()
        effect_columns = cursor.read_uint8() + 1
        channels.append(ParsedChannelHeader(channel_id=channel_id, effect_columns=effect_columns))

    return ParsedHeader(track_count=track_count, track_titles=track_titles, channels=channels)


def _parse_instruments(payload: bytes) -> List[ParsedInstrument]:
    cursor = _Cursor(payload)
    count = cursor.read_int32()
    instruments: List[ParsedInstrument] = []
    for _ in range(count):
        index = cursor.read_int32()
        instrument_type = cursor.read_uint8()
        sequence_count = cursor.read_int32()
        refs: Dict[int, Tuple[int, int]] = {}
        for kind in range(sequence_count):
            enabled = cursor.read_uint8()
            sequence_index = cursor.read_uint8()
            refs[kind] = (enabled, sequence_index)
        cursor.skip(DPCM_KEY_ASSIGNMENTS * DPCM_KEY_BYTES)
        name = cursor.counted_string()
        instruments.append(
            ParsedInstrument(index=index, instrument_type=instrument_type, sequence_refs=refs, name=name)
        )

    return instruments


def _parse_sequences(payload: bytes) -> List[ParsedSequence]:
    cursor = _Cursor(payload)
    count = cursor.read_int32()
    sequences: List[ParsedSequence] = []
    for _ in range(count):
        index = cursor.read_int32()
        sequence_type = cursor.read_int32()
        item_count = cursor.read_uint8()
        loop_point = cursor.read_int32()
        items = [cursor.read_int8() for _ in range(item_count)]
        sequences.append(
            ParsedSequence(
                index=index,
                sequence_type=sequence_type,
                items=items,
                loop_point=loop_point,
                release_point=-1,
                setting=0,
            )
        )
    for sequence in sequences:
        sequence.release_point = cursor.read_int32()
        sequence.setting = cursor.read_int32()

    return sequences


def _parse_frames(payload: bytes, channel_count: int) -> ParsedFrames:
    cursor = _Cursor(payload)
    frame_count = cursor.read_int32()
    speed = cursor.read_int32()
    tempo = cursor.read_int32()
    pattern_length = cursor.read_int32()
    order = [tuple(cursor.read_uint8() for _ in range(channel_count)) for _ in range(frame_count)]
    return ParsedFrames(
        frame_count=frame_count,
        speed=speed,
        tempo=tempo,
        pattern_length=pattern_length,
        order=order,
    )


def _parse_patterns(payload: bytes, effect_columns_by_channel: Dict[int, int]) -> List[ParsedPattern]:
    cursor = _Cursor(payload)
    patterns: List[ParsedPattern] = []
    while cursor.peek(1):
        track = cursor.read_int32()
        channel = cursor.read_int32()
        index = cursor.read_int32()
        row_count = cursor.read_int32()
        rows: List[ParsedRow] = []
        for _ in range(row_count):
            row_number = cursor.read_int32()
            note = cursor.read_int8()
            octave = cursor.read_int8()
            instrument = cursor.read_int8()
            volume = cursor.read_int8()
            effects = [(cursor.read_int8(), cursor.read_int8()) for _ in range(effect_columns_by_channel[channel])]
            rows.append(
                ParsedRow(
                    row_number=row_number,
                    note=note,
                    octave=octave,
                    instrument=instrument,
                    volume=volume,
                    effects=effects,
                )
            )
        patterns.append(ParsedPattern(track=track, channel=channel, index=index, rows=rows))
    return patterns


def _parse_comments(payload: bytes) -> str:
    cursor = _Cursor(payload)
    cursor.read_int32()
    return cursor.terminated_string()


def parse_ftm(data: bytes) -> ParsedModule:
    cursor = _Cursor(data)
    magic = cursor.read(len(FTM_MAGIC))
    assert magic == FTM_MAGIC
    version = cursor.read_uint32()

    payloads, versions = _read_blocks(cursor)

    params = _parse_params(payloads["PARAMS"])
    info = _parse_info(payloads["INFO"])
    header = _parse_header(payloads["HEADER"], params.channel_count)
    instruments = _parse_instruments(payloads["INSTRUMENTS"])
    sequences = _parse_sequences(payloads["SEQUENCES"])
    frames = _parse_frames(payloads["FRAMES"], params.channel_count)
    effect_columns_by_channel = {channel.channel_id: channel.effect_columns for channel in header.channels}
    patterns = _parse_patterns(payloads["PATTERNS"], effect_columns_by_channel)
    dpcm_sample_count = _Cursor(payloads["DPCM SAMPLES"]).read_uint8()
    comment = _parse_comments(payloads["COMMENTS"])

    return ParsedModule(
        version=version,
        params=params,
        info=info,
        header=header,
        instruments=instruments,
        sequences=sequences,
        frames=frames,
        patterns=patterns,
        dpcm_sample_count=dpcm_sample_count,
        comment=comment,
        block_versions=versions,
    )


# The FTI parser lives in test_fti.py; SEQUENCE_COUNT_2A03 is re-exported for tests
# that assert the instrument body shape.
EXPECTED_SEQUENCE_COUNT = SEQUENCE_COUNT_2A03
