import struct
from pathlib import Path
from typing import Optional, Union

import numpy as np


def write_fti(
    filename: Union[str, Path],
    instrument_name: str,
    volume: Optional[np.ndarray] = None,
    arpeggio: Optional[np.ndarray] = None,
    pitch: Optional[np.ndarray] = None,
    hi_pitch: Optional[np.ndarray] = None,
    duty_cycle: Optional[np.ndarray] = None,
    volume_loop: int = -1,
    arpeggio_loop: int = -1,
    pitch_loop: int = -1,
    hi_pitch_loop: int = -1,
    duty_cycle_loop: int = -1,
    volume_release: int = -1,
    arpeggio_release: int = -1,
    pitch_release: int = -1,
    hi_pitch_release: int = -1,
    duty_cycle_release: int = -1,
    volume_setting: int = 0,
    arpeggio_setting: int = 0,
    pitch_setting: int = 0,
    hi_pitch_setting: int = 0,
    duty_cycle_setting: int = 0,
):
    with open(filename, "wb") as file:
        file.write(b"FTI")
        file.write(b"2.4")

        instrument_type_2a03 = 1
        file.write(struct.pack("<B", instrument_type_2a03))

        name_bytes = instrument_name.encode("utf-8")
        file.write(struct.pack("<I", len(name_bytes)))
        file.write(name_bytes)

        sequences = [
            (volume, volume_loop, volume_release, volume_setting),
            (arpeggio, arpeggio_loop, arpeggio_release, arpeggio_setting),
            (pitch, pitch_loop, pitch_release, pitch_setting),
            (hi_pitch, hi_pitch_loop, hi_pitch_release, hi_pitch_setting),
            (duty_cycle, duty_cycle_loop, duty_cycle_release, duty_cycle_setting),
        ]

        sequence_count_2a03 = 5
        file.write(struct.pack("<b", sequence_count_2a03))

        for sequence_data, loop_point, release_point, setting in sequences:
            if sequence_data is not None and len(sequence_data) > 0:
                sequence_enabled = 1
                file.write(struct.pack("<b", sequence_enabled))

                sequence_length = len(sequence_data)
                file.write(struct.pack("<I", sequence_length))

                file.write(struct.pack("<i", loop_point))
                file.write(struct.pack("<i", release_point))
                file.write(struct.pack("<I", setting))

                for item in sequence_data:
                    file.write(struct.pack("<b", int(item)))
            else:
                sequence_disabled = 0
                file.write(struct.pack("<b", sequence_disabled))

        dpcm_assignment_count = 0
        dpcm_sample_count = 0
        file.write(struct.pack("<I", dpcm_assignment_count))
        file.write(struct.pack("<I", dpcm_sample_count))
