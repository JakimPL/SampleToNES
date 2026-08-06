from sampletones_core.formats.famitracker.binary import BinaryWriter
from sampletones_core.formats.famitracker.model.instrument import Instrument2A03
from sampletones_core.formats.famitracker.model.sequence import InstrumentSequence
from sampletones_core.formats.famitracker.specification.file import FTI_MAGIC, FTI_VERSION
from sampletones_core.formats.famitracker.specification.instruments import (
    EMPTY_DPCM_ASSIGNMENTS,
    EMPTY_DPCM_SAMPLES,
    INSTRUMENT_TYPE_2A03,
)
from sampletones_core.formats.famitracker.specification.sequences import (
    SEQUENCE_COUNT_2A03,
    SEQUENCE_DISABLED,
    SEQUENCE_ENABLED,
    SequenceKind,
)
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import save_binary


def _write_header(writer: BinaryWriter) -> None:
    writer.write_bytes(FTI_MAGIC)
    writer.write_bytes(FTI_VERSION)


def _write_type_and_name(
    writer: BinaryWriter,
    instrument: Instrument2A03,
) -> None:
    writer.write_uint8(INSTRUMENT_TYPE_2A03)
    writer.write_counted_string(instrument.name)


def _write_sequence(
    writer: BinaryWriter,
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


def _write_sequences(writer: BinaryWriter, instrument: Instrument2A03) -> None:
    writer.write_int8(SEQUENCE_COUNT_2A03)
    for kind in SequenceKind:
        _write_sequence(writer, instrument.sequences[kind])


def _write_empty_dpcm_section(writer: BinaryWriter) -> None:
    writer.write_uint32(EMPTY_DPCM_ASSIGNMENTS)
    writer.write_uint32(EMPTY_DPCM_SAMPLES)


def instrument_to_fti_bytes(instrument: Instrument2A03) -> bytes:
    """Serializes a 2A03 instrument to the FamiTracker ``.fti`` byte layout."""
    writer = BinaryWriter()
    _write_header(writer)
    _write_type_and_name(writer, instrument)
    _write_sequences(writer, instrument)
    _write_empty_dpcm_section(writer)
    return writer.data


def write_fti(filepath: Pathlike, instrument: Instrument2A03) -> None:
    """Writes a 2A03 instrument to a ``.fti`` file."""
    save_binary(filepath, instrument_to_fti_bytes(instrument))
