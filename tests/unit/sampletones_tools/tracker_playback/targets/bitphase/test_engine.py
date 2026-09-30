import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Final, List, Optional, Sequence

import pytest
from pydantic import ValidationError

from sampletones_core.constants.enums import ChannelName
from sampletones_tools.tracker_playback.paths import BITPHASE_TRACE_SCRIPT_PATH
from sampletones_tools.tracker_playback.targets.bitphase import engine
from sampletones_tools.tracker_playback.targets.bitphase.engine import (
    CHECKOUT_FILES,
    TSX_CLI,
    BitphaseCheckout,
    BitphaseEngine,
    EngineError,
    read_driver_trace,
)
from sampletones_tools.tracker_playback.trace.sound import ABSENT_REGISTER, ChannelSound, TickPosition

NODE: Final[Path] = Path("node")
SILENT_CHANNEL: Final[Dict[str, Any]] = {
    "enabled": False,
    "period": 0,
    "volume": 0,
    "duty": 2,
    "noise_period": 0,
    "noise_mode": False,
}


def _channel(**values: Any) -> Dict[str, Any]:
    return {**SILENT_CHANNEL, **values}


def _trace_text(*channels: Dict[str, Any], frame: int = 0, row: int = 0) -> str:
    return json.dumps({"ticks": [{"frame": frame, "row": row, "channels": list(channels)}]})


def _checkout(root: Path) -> BitphaseCheckout:
    for relative in CHECKOUT_FILES:
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).touch()

    return BitphaseCheckout.located(root)


class TestReadDriverTrace:
    def test_each_tick_keeps_the_frame_and_row_bitphase_played_it_at(self) -> None:
        trace = read_driver_trace(_trace_text(*(SILENT_CHANNEL,) * 4, frame=2, row=5))

        assert trace.positions == (TickPosition(frame=2, row=5),)
        assert set(trace.channels) == set(ChannelName.items())

    def test_a_pulse_timer_is_its_period_less_one(self) -> None:
        pulse = _channel(enabled=True, period=428, volume=9, duty=1)

        trace = read_driver_trace(_trace_text(pulse, pulse, SILENT_CHANNEL, SILENT_CHANNEL))

        expected = ChannelSound(audible=True, period=427, volume=9, timbre=1)
        assert trace.channels[ChannelName.PULSE1] == (expected,)
        assert trace.channels[ChannelName.PULSE2] == (expected,)

    def test_a_triangle_timer_is_its_period_whole(self) -> None:
        triangle = _channel(enabled=True, period=855, volume=15)

        trace = read_driver_trace(_trace_text(SILENT_CHANNEL, SILENT_CHANNEL, triangle, SILENT_CHANNEL))

        assert trace.channels[ChannelName.TRIANGLE] == (
            ChannelSound(audible=True, period=855, volume=ABSENT_REGISTER, timbre=ABSENT_REGISTER),
        )

    def test_a_tone_channel_enabled_at_period_zero_is_silent(self) -> None:
        stopped = _channel(enabled=True, period=0, volume=15)

        trace = read_driver_trace(_trace_text(stopped, stopped, stopped, SILENT_CHANNEL))

        for channel in (ChannelName.PULSE1, ChannelName.PULSE2, ChannelName.TRIANGLE):
            assert not trace.channels[channel][0].audible

    def test_the_noise_sounds_while_enabled_at_its_register_period_and_mode(self) -> None:
        noise = _channel(enabled=True, volume=7, noise_period=6, noise_mode=True)

        trace = read_driver_trace(_trace_text(SILENT_CHANNEL, SILENT_CHANNEL, SILENT_CHANNEL, noise))

        assert trace.channels[ChannelName.NOISE] == (ChannelSound(audible=True, period=6, volume=7, timbre=1),)

    def test_text_the_script_never_writes_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            read_driver_trace(json.dumps({"ticks": [{"frame": 0, "row": 0, "channels": []}]}))


class TestBitphaseCheckout:
    def test_a_checkout_holding_every_file_the_trace_loads_is_located(self, tmp_path: Path) -> None:
        assert _checkout(tmp_path).root == tmp_path

    def test_a_checkout_without_its_packages_is_refused_naming_what_it_lacks(self, tmp_path: Path) -> None:
        _checkout(tmp_path)
        (tmp_path / TSX_CLI).unlink()

        with pytest.raises(EngineError, match="pnpm install") as refusal:
            BitphaseCheckout.located(tmp_path)

        assert str(TSX_CLI) in str(refusal.value)


class TestBitphaseEngine:
    def test_an_absent_node_is_reported(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        _checkout(tmp_path)
        monkeypatch.setattr(engine, "locate_program", lambda program: None)

        with pytest.raises(EngineError, match="node"):
            BitphaseEngine.located(tmp_path)

    def test_the_engine_takes_the_node_this_system_has(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        _checkout(tmp_path)
        monkeypatch.setattr(engine, "locate_program", lambda program: Path("/usr/bin") / program)

        located = BitphaseEngine.located(tmp_path)

        assert located.node == Path("/usr/bin") / "node"

    def test_the_trace_script_runs_through_the_checkouts_own_tsx(self, tmp_path: Path) -> None:
        played = BitphaseEngine(node=NODE, checkout=_checkout(tmp_path))
        document = tmp_path / "song.btp"
        output = tmp_path / "song.json"

        assert played.command(document, output) == [
            str(NODE),
            str(tmp_path / TSX_CLI),
            str(BITPHASE_TRACE_SCRIPT_PATH),
            str(tmp_path),
            str(document),
            str(output),
        ]

    def test_the_script_is_handed_absolute_paths(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        played = BitphaseEngine(node=NODE, checkout=_checkout(tmp_path / "checkout"))
        monkeypatch.chdir(tmp_path)

        command = played.command(Path("run") / "song.btp", Path("run") / "song.json")

        assert [Path(argument) for argument in command[-2:]] == [
            tmp_path / "run" / "song.btp",
            tmp_path / "run" / "song.json",
        ]

    def test_a_trace_is_read_from_the_file_the_run_writes(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        played = BitphaseEngine(node=NODE, checkout=_checkout(tmp_path))
        output = tmp_path / "song.json"
        runs: List[Optional[Path]] = []

        def run(command: Sequence[str], *, cwd: Path, **options: Any) -> None:
            runs.append(cwd)
            Path(command[-1]).write_text(_trace_text(*(SILENT_CHANNEL,) * 4), encoding="utf-8")

        monkeypatch.setattr(engine.subprocess, "run", run)

        trace = played.trace(tmp_path / "song.btp", output)

        assert runs == [tmp_path]
        assert trace.ticks == 1

    def test_a_failed_run_is_reported_with_what_it_printed(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        played = BitphaseEngine(node=NODE, checkout=_checkout(tmp_path))

        def run(command: Sequence[str], **options: Any) -> None:
            raise subprocess.CalledProcessError(1, list(command), stderr="Song is empty")

        monkeypatch.setattr(engine.subprocess, "run", run)

        with pytest.raises(EngineError, match="Song is empty"):
            played.trace(tmp_path / "song.btp", tmp_path / "song.json")
