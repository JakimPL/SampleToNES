from pathlib import Path
from typing import Optional, Protocol

import numpy as np

from sampletones_application.logic.export.instrument.source import ExportableInstrument
from sampletones_application.logic.reconstruction.data import ReconstructionData
from sampletones_application.view_model.reconstruction.envelopes import ChannelEnvelopesViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.naming import instrument_slice_name
from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.request import InstrumentExport, InstrumentSource, SampleExport


class ExportServiceProtocol(Protocol):
    """The slice of the export service the reconstruction panel logic drives.

    Typing the collaborator structurally keeps the logic layer independent of
    the service implementation; the composition root supplies the real service.
    """

    def export_wav(
        self,
        filepath: Path,
        sample_rate: int,
        audio: np.ndarray,
    ) -> None: ...

    def export_instrument(
        self,
        destination: Path,
        backend: ExportBackend,
        request: InstrumentExport,
    ) -> None: ...

    def export_sample(
        self,
        destination: Path,
        backend: ExportBackend,
        request: SampleExport,
    ) -> None: ...


def channel_instrument(
    reconstruction_data: ReconstructionData,
    envelopes: ChannelEnvelopesViewModel,
    channel_name: ChannelName,
) -> Optional[ExportableInstrument]:
    """The reconstruction's ``channel_name`` slice, ready to be given a destination, or ``None`` where that
    channel describes no frame and is written nowhere.

    A reconstruction has no loop flag of its own — that belongs to a sample placed in a project — so
    the instrument plays its envelopes once.
    """
    features = envelopes[channel_name]
    if not features.has_frames:
        return None

    library = reconstruction_data.config.library
    return ExportableInstrument(
        name=instrument_slice_name(reconstruction_data.name, channel_name),
        source=InstrumentSource(
            channel=channel_name,
            features=features,
            nes_frequency=library.nes_frequency,
            tuning=library.tuning,
        ),
    )


def sample_instruments(
    reconstruction_data: ReconstructionData,
    envelopes: ChannelEnvelopesViewModel,
    name: str,
) -> SampleExport:
    """The slice of every channel of the reconstruction describing a frame, as one export named ``name``.

    Each slice takes its channel suffix from the name. A reconstruction's envelopes state no repeat
    of their own, so each dimension holds its final value once it runs out and the trailing silence
    releases the note. A backend sounding the export on its own measures its pitches from the tuning
    the reconstruction was built with, which keeps what it plays in tune with the reconstruction.
    """
    library = reconstruction_data.config.library
    return SampleExport(
        name=name,
        instruments=tuple(
            InstrumentExport(
                name=instrument_slice_name(name, channel_name),
                channel=channel_name,
                features=feature,
                nes_frequency=library.nes_frequency,
                tuning=library.tuning,
            )
            for channel_name, feature in envelopes.channels.items()
            if feature.has_frames
        ),
        nes_frequency=library.nes_frequency,
        tuning=library.tuning,
    )
