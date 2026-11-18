from pathlib import Path
from typing import Final, List

import pytest

from assets.footage.mastering import (
    Loudness,
    LoudnessReadingError,
    decibel_gain,
    limiter_command,
    loudness_command,
    parse_loudness,
)
from sampletones_tools.ffmpeg import FFMPEG

REPORT: Final[str] = """[Parsed_ebur128_0 @ 0x1] t: 1.0 TARGET:-23 LUFS M: -20.0 S: -20.0 I: -20.0 LUFS
[Parsed_ebur128_0 @ 0x1] Summary:

  Integrated loudness:
    I:         -16.0 LUFS
    Threshold: -26.1 LUFS

  True peak:
    Peak:       -1.6 dBFS
"""


class TestLoudnessReport:
    def test_the_summary_gives_the_integrated_loudness_and_the_true_peak(self) -> None:
        assert parse_loudness(REPORT) == Loudness(integrated=-16.0, true_peak=-1.6)

    def test_a_report_without_a_summary_is_refused(self) -> None:
        with pytest.raises(LoudnessReadingError):
            parse_loudness("[Parsed_ebur128_0 @ 0x1] t: 1.0 I: -20.0 LUFS")


class TestCommands:
    def test_the_meter_reads_the_file_through_ffmpeg(self) -> None:
        command = loudness_command(Path("sound.wav"))

        assert command[0] == FFMPEG
        assert "sound.wav" in command
        assert any("ebur128=peak=true" in argument for argument in command)

    def test_the_limiter_raises_the_sound_before_holding_its_peaks(self) -> None:
        command = limiter_command(Path("in.wav"), Path("out.wav"), gain_decibels=2.5)
        chain = command[command.index("-af") + 1]

        assert chain.index("volume=2.500000dB") < chain.index("alimiter")
        assert command[-1] == "out.wav"

    @pytest.mark.parametrize(
        "command",
        [
            loudness_command(Path("sound.wav")),
            limiter_command(Path("in.wav"), Path("out.wav"), gain_decibels=0.0),
        ],
    )
    def test_every_command_runs_unattended_and_overwrites_its_target(self, command: List[str]) -> None:
        assert {"-nostdin", "-y"} <= set(command)


class TestDecibelGain:
    def test_twenty_decibels_is_ten_times(self) -> None:
        assert decibel_gain(20.0) == pytest.approx(10.0)
