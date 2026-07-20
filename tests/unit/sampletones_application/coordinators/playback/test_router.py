from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import pytest

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.coordinators.playback.router import PlaybackRouter

IDLE = "idle"
PLAYING = "playing"
PAUSED = "paused"


class FakeSource:
    """A test double for an intentional playback source.

    ``is_playing`` reports engagement — owning the output whether sounding or held paused — matching
    the ownership-aware convention the real sources follow.
    """

    def __init__(self, *, loaded: bool = False, state: str = IDLE) -> None:
        self._loaded = loaded
        self.state = state
        self.calls: List[str] = []

    def play(self) -> None:
        self.calls.append("play")
        self.state = PLAYING

    def pause_or_resume(self) -> None:
        self.calls.append("pause_or_resume")
        if self.state == PAUSED:
            self.state = PLAYING
        elif self.state == PLAYING:
            self.state = PAUSED
        else:
            self.state = PLAYING

    def stop(self) -> None:
        self.calls.append("stop")
        self.state = IDLE

    def is_playing(self) -> bool:
        return self.state in (PLAYING, PAUSED)

    def is_paused(self) -> bool:
        return self.state == PAUSED

    def is_loaded(self) -> bool:
        return self._loaded


class FakeDevice:
    def __init__(self, *, playing: bool = False) -> None:
        self.playing = playing
        self.stop_calls = 0

    def is_playing(self) -> bool:
        return self.playing

    def stop(self) -> None:
        self.stop_calls += 1
        self.playing = False


class FakeLanguageManager:
    """Resolves a label key to its element, so ``play_label`` is checkable against a MenuElements."""

    def __getitem__(self, key: Sequence[object]) -> object:
        return key[-1]


def _router(
    *,
    active: Optional[FakeSource],
    sources: Sequence[FakeSource],
    device: FakeDevice,
) -> PlaybackRouter:
    return PlaybackRouter(
        sources=sources,
        active_source_resolver=lambda: active,
        audio_device_manager=device,  # type: ignore[arg-type]
        language_manager=FakeLanguageManager(),  # type: ignore[arg-type]
    )


class TestTransportCommands:
    def test_space_resumes_the_engaged_source_from_a_sourceless_tab(self) -> None:
        reconstruction = FakeSource(loaded=True, state=PAUSED)
        router = _router(active=None, sources=[reconstruction], device=FakeDevice())

        router.play()

        assert reconstruction.state == PLAYING
        assert reconstruction.calls == ["pause_or_resume"]

    def test_space_starts_the_active_tab_source_when_it_is_idle(self) -> None:
        active = FakeSource(loaded=True, state=IDLE)
        background = FakeSource(loaded=True, state=PLAYING)
        router = _router(active=active, sources=[active, background], device=FakeDevice())

        router.play()

        assert active.state == PLAYING
        assert background.calls == []

    def test_space_pauses_the_active_tab_source_when_it_is_playing(self) -> None:
        active = FakeSource(loaded=True, state=PLAYING)
        router = _router(active=active, sources=[active], device=FakeDevice())

        router.play()

        assert active.state == PAUSED

    def test_space_does_nothing_without_a_target(self) -> None:
        unloaded = FakeSource(loaded=False, state=IDLE)
        device = FakeDevice(playing=True)
        router = _router(active=None, sources=[unloaded], device=device)

        router.play()

        assert unloaded.calls == []
        assert device.stop_calls == 0

    def test_play_from_start_starts_the_active_tab_source(self) -> None:
        active = FakeSource(loaded=True, state=PLAYING)
        router = _router(active=active, sources=[active], device=FakeDevice())

        router.play_from_start()

        assert active.calls == ["play"]

    def test_play_from_start_does_nothing_without_an_active_source(self) -> None:
        background = FakeSource(loaded=True, state=PLAYING)
        router = _router(active=None, sources=[background], device=FakeDevice())

        router.play_from_start()

        assert background.calls == []

    def test_stop_stops_the_engaged_source_and_the_device(self) -> None:
        engaged = FakeSource(loaded=True, state=PLAYING)
        device = FakeDevice(playing=True)
        router = _router(active=None, sources=[engaged], device=device)

        router.stop()

        assert engaged.calls == ["stop"]
        assert device.stop_calls == 1

    def test_stop_silences_a_preview_when_no_source_is_engaged(self) -> None:
        idle = FakeSource(loaded=True, state=IDLE)
        device = FakeDevice(playing=True)
        router = _router(active=None, sources=[idle], device=device)

        router.stop()

        assert idle.calls == []
        assert device.stop_calls == 1


@dataclass(frozen=True)
class StateCase:
    label: str
    active: Optional[str]
    background: Optional[str]
    preview: bool
    play_enabled: bool
    play_from_start_enabled: bool
    pause_enabled: bool
    paused: bool
    stop_enabled: bool
    play_label: MenuElements = field(default=MenuElements.ITEM_PLAYBACK_PLAY)


STATE_CASES = [
    StateCase(
        "silent",
        active=None,
        background=None,
        preview=False,
        play_enabled=False,
        play_from_start_enabled=False,
        pause_enabled=False,
        paused=False,
        stop_enabled=False,
    ),
    StateCase(
        "preview_only",
        active=None,
        background=None,
        preview=True,
        play_enabled=False,
        play_from_start_enabled=False,
        pause_enabled=False,
        paused=False,
        stop_enabled=True,
    ),
    StateCase(
        "active_idle",
        active=IDLE,
        background=None,
        preview=False,
        play_enabled=True,
        play_from_start_enabled=True,
        pause_enabled=False,
        paused=False,
        stop_enabled=False,
    ),
    StateCase(
        "active_playing",
        active=PLAYING,
        background=None,
        preview=False,
        play_enabled=True,
        play_from_start_enabled=True,
        pause_enabled=True,
        paused=False,
        stop_enabled=True,
        play_label=MenuElements.ITEM_PLAYBACK_PAUSE,
    ),
    StateCase(
        "active_paused",
        active=PAUSED,
        background=None,
        preview=False,
        play_enabled=True,
        play_from_start_enabled=True,
        pause_enabled=True,
        paused=True,
        stop_enabled=True,
        play_label=MenuElements.ITEM_PLAYBACK_RESUME,
    ),
    StateCase(
        "background_playing_on_sourceless_tab",
        active=None,
        background=PLAYING,
        preview=False,
        play_enabled=True,
        play_from_start_enabled=False,
        pause_enabled=True,
        paused=False,
        stop_enabled=True,
        play_label=MenuElements.ITEM_PLAYBACK_PAUSE,
    ),
    StateCase(
        "background_paused_on_sourceless_tab",
        active=None,
        background=PAUSED,
        preview=False,
        play_enabled=True,
        play_from_start_enabled=False,
        pause_enabled=True,
        paused=True,
        stop_enabled=True,
        play_label=MenuElements.ITEM_PLAYBACK_RESUME,
    ),
    StateCase(
        "active_idle_over_background_playing",
        active=IDLE,
        background=PLAYING,
        preview=False,
        play_enabled=True,
        play_from_start_enabled=True,
        pause_enabled=False,
        paused=False,
        stop_enabled=True,
    ),
]


class TestTransportState:
    """The toolbar/menu state describes the target, and Stop follows any audible output."""

    @pytest.mark.parametrize("case", STATE_CASES, ids=lambda case: case.label)
    def test_state(self, case: StateCase) -> None:
        active = FakeSource(loaded=True, state=case.active) if case.active is not None else None
        background = FakeSource(loaded=True, state=case.background) if case.background is not None else None
        sources = [source for source in (active, background) if source is not None]
        router = _router(active=active, sources=sources, device=FakeDevice(playing=case.preview))

        assert router.is_play_enabled is case.play_enabled
        assert router.is_play_from_start_enabled is case.play_from_start_enabled
        assert router.is_pause_enabled is case.pause_enabled
        assert router.is_paused is case.paused
        assert router.is_stop_enabled is case.stop_enabled
        assert router.play_label == case.play_label
