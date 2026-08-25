from typing import Dict

from pydantic import ValidationError

from sampletones_core.formats.binary import BinaryReader
from sampletones_core.formats.famitracker.binary import FamiTrackerWriter
from sampletones_core.formats.famitracker.model.instrument import Instrument2A03
from sampletones_core.formats.famitracker.model.sequence import InstrumentSequence
from sampletones_core.formats.famitracker.specification.file import (
    FTI_MAGIC,
    FTI_VERSION,
)
from sampletones_core.formats.famitracker.specification.instruments import (
    EMPTY_DPCM_ASSIGNMENTS,
    EMPTY_DPCM_SAMPLES,
    INSTRUMENT_TYPE_2A03,
    STANDALONE_INSTRUMENT_INDEX,
)
from sampletones_core.formats.famitracker.specification.sequences import (
    SEQUENCE_COUNT_2A03,
    SEQUENCE_DISABLED,
    SEQUENCE_ENABLED,
    SequenceKind,
)
from sampletones_shared.exceptions import (
    IncompatibleInstrumentVersionError,
    InvalidInstrumentValuesError,
    MalformedInstrumentError,
    NotAnInstrumentFileError,
    TruncatedDataError,
    UnsupportedInstrumentTypeError,
)
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import load_binary, save_binary


def _write_header(writer: FamiTrackerWriter) -> None:
    writer.write_bytes(FTI_MAGIC)
    writer.write_bytes(FTI_VERSION)


def _write_type_and_name(
    writer: FamiTrackerWriter,
    instrument: Instrument2A03,
) -> None:
    writer.write_uint8(INSTRUMENT_TYPE_2A03)
    writer.write_counted_string(instrument.name)


def _write_sequence(
    writer: FamiTrackerWriter,
    sequence: InstrumentSequence,
) -> None:
    if not sequence.enabled:
        writer.write_int8(SEQUENCE_DISABLED)
        return

    writer.write_int8(SEQUENCE_ENABLED)
    writer.write_uint32(len(sequence.items))
    writer.write_int32(sequence.loop_point)
    writer.write_int32(sequence.release_point)
    writer.write_uint32(sequence.setting)
    for item in sequence.items:
        writer.write_int8(item)


def _write_sequences(writer: FamiTrackerWriter, instrument: Instrument2A03) -> None:
    writer.write_int8(SEQUENCE_COUNT_2A03)
    for kind in SequenceKind:
        _write_sequence(writer, instrument.sequences[kind])


def _write_empty_dpcm_section(writer: FamiTrackerWriter) -> None:
    writer.write_uint32(EMPTY_DPCM_ASSIGNMENTS)
    writer.write_uint32(EMPTY_DPCM_SAMPLES)


def instrument_to_fti_bytes(instrument: Instrument2A03) -> bytes:
    """Serializes a 2A03 instrument to the FamiTracker ``.fti`` byte layout."""
    writer = FamiTrackerWriter()
    _write_header(writer)
    _write_type_and_name(writer, instrument)
    _write_sequences(writer, instrument)
    _write_empty_dpcm_section(writer)
    return writer.data


def write_fti(filepath: Pathlike, instrument: Instrument2A03) -> None:
    """Writes a 2A03 instrument to a ``.fti`` file."""
    save_binary(filepath, instrument_to_fti_bytes(instrument))


def _read_header(reader: BinaryReader) -> None:
    magic = reader.read_bytes(len(FTI_MAGIC))
    if magic != FTI_MAGIC:
        raise NotAnInstrumentFileError(f"An instrument file opens with {FTI_MAGIC!r}, this one with {magic!r}")

    version = reader.read_bytes(len(FTI_VERSION))
    if version != FTI_VERSION:
        raise IncompatibleInstrumentVersionError(
            f"Instrument file version mismatch: expected {FTI_VERSION!r}, got {version!r}.",
            expected_version=FTI_VERSION.decode("ascii"),
            actual_version=version.decode("ascii", errors="replace"),
        )


def _read_type_and_name(reader: BinaryReader) -> str:
    instrument_type = reader.read_uint8()
    if instrument_type != INSTRUMENT_TYPE_2A03:
        raise UnsupportedInstrumentTypeError(
            f"Instrument type {instrument_type} is read here only as the 2A03 type {INSTRUMENT_TYPE_2A03}"
        )

    return reader.read_counted_string()


def _read_sequence(
    reader: BinaryReader,
    kind: SequenceKind,
) -> InstrumentSequence:
    if reader.read_int8() == SEQUENCE_DISABLED:
        return InstrumentSequence(kind=kind)

    length = reader.read_uint32()
    loop_point = reader.read_int32()
    release_point = reader.read_int32()
    setting = reader.read_uint32()

    return InstrumentSequence(
        kind=kind,
        items=tuple(reader.read_int8() for _ in range(length)),
        loop_point=loop_point,
        release_point=release_point,
        setting=setting,
    )


def _read_sequences(
    reader: BinaryReader,
) -> Dict[SequenceKind, InstrumentSequence]:
    count = reader.read_int8()
    if count != SEQUENCE_COUNT_2A03:
        raise MalformedInstrumentError(
            f"A 2A03 instrument carries {SEQUENCE_COUNT_2A03} sequences, this one states {count}"
        )

    sequences: Dict[SequenceKind, InstrumentSequence] = {}
    for kind in SequenceKind:
        sequences[kind] = _read_sequence(reader, kind)

    return sequences


def _read_dpcm_section(reader: BinaryReader) -> None:
    """Steps past the key assignments and samples a file states behind its sequences."""
    reader.read_uint32()
    reader.read_uint32()


def _read_instrument(reader: BinaryReader) -> Instrument2A03:
    _read_header(reader)
    name = _read_type_and_name(reader)
    sequences = _read_sequences(reader)
    _read_dpcm_section(reader)

    return Instrument2A03(
        index=STANDALONE_INSTRUMENT_INDEX,
        name=name,
        sequences=sequences,
    )


def fti_bytes_to_instrument(data: bytes) -> Instrument2A03:
    """Reads a 2A03 instrument from the FamiTracker ``.fti`` byte layout.

    The five sequences and the name are what a file carries into an instrument, taken in the
    order :func:`instrument_to_fti_bytes` writes them. A file states its own DPCM key
    assignments and samples behind them, which a 2A03 instrument here leaves to the file.

    Args:
        data: The bytes of a ``.fti`` file.

    Returns:
        Instrument2A03: The instrument the bytes describe, numbered as a standalone file's.

    Raises:
        NotAnInstrumentFileError: If the data opens with something other than the signature.
        IncompatibleInstrumentVersionError: If the file states another layout version.
        UnsupportedInstrumentTypeError: If the file states a chip other than the 2A03.
        MalformedInstrumentError: If the file departs from the layout its own fields describe.
        InvalidInstrumentValuesError: If a sequence carries more items than one holds.
    """
    try:
        return _read_instrument(BinaryReader(data))
    except (TruncatedDataError, UnicodeDecodeError) as exception:
        raise MalformedInstrumentError(
            f"The instrument file ends inside the layout it states: {exception}"
        ) from exception
    except ValidationError as exception:
        raise InvalidInstrumentValuesError(
            f"Failed to read an instrument due to validation error: {exception}",
            exception,
        ) from exception


def read_fti(filepath: Pathlike) -> Instrument2A03:
    """Reads a 2A03 instrument from a ``.fti`` file.

    Raises:
        FileNotFoundError: If no file stands at ``filepath``.
    """
    return fti_bytes_to_instrument(load_binary(filepath))
