from functools import partial
from pathlib import Path
from typing import List

from assets.footage.composition import Box, Ground, composed
from assets.footage.frames import filmed, frame_path, write_frame
from assets.footage.shoot import Take
from assets.footage.shot import MARGIN, REEL, panes
from assets.footage.specification import Listening
from assets.stage.camera import Camera
from assets.stage.frames import eight_bit
from automation.dearpygui.geometry import Rect
from automation.screen import Screen
from automation.steps.reconstructions import (
    expect_open,
    expect_the_playhead_at,
    put_the_playhead_at,
    reconstruction_shade,
    wait_for_the_fade_to_end,
)
from automation.vocabulary.playback import SOURCE_SWITCHES
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId


class MovedPanesError(AssertionError):
    """Raised when a pane moves or changes size partway through the footage, as a column scrolling would."""


class Filming:
    """Films the Reconstructions tab for one take, frame by frame.

    Each frame shows the playhead on its tick, reached by stepping the paused playback one tick at a time,
    under the listening the timeline sets for it: the source the switch names and the stem rows ticked. The
    screen is cut into the shot's panes and laid on the reel's frame. The take begins with the first frame
    missing from its folder, so a run cut short resumes where it stopped.
    """

    def __init__(self, screen: Screen, take: Take, ground: Ground) -> None:
        self._screen = screen
        self._take = take
        self._ground = ground
        self._camera = Camera(screen)

    def film(self, document: Path) -> None:
        """Films the frames of the take still missing, with ``document`` open."""
        screen = self._screen
        schedule = self._take.shoot.schedule
        expect_open(screen, document)
        unfaded = reconstruction_shade(screen)
        start = filmed(self._take.frames)
        listening = schedule.listening(start)
        self._listen(listening, unfaded)
        put_the_playhead_at(screen, self._sample(start), tick_length=self._take.shoot.tick_length)
        self._camera.rest()
        pixels = eight_bit(self._camera.pixels())
        boxes = self._boxes(pixels.shape[1], pixels.shape[0])

        for frame in range(start, self._take.stop):
            if frame > start:
                if schedule.listening(frame) != listening:
                    listening = schedule.listening(frame)
                    self._listen(listening, unfaded)
                    self._camera.rest()
                    if self._boxes(pixels.shape[1], pixels.shape[0]) != boxes:
                        raise MovedPanesError("A pane moved; a viewport holding every card whole keeps them still")

                for _ in range(schedule.ticks_per_frame):
                    screen.press_shortcut(ShortcutId.STEP_FORWARD)
                expect_the_playhead_at(screen, self._sample(frame))
                pixels = eight_bit(self._camera.pixels())

            write_frame(composed(pixels, boxes, REEL, self._ground), frame_path(self._take.frames, frame))

    def _sample(self, frame: int) -> int:
        return self._take.shoot.schedule.tick(frame) * self._take.shoot.tick_length

    def _listen(self, listening: Listening, unfaded: str) -> None:
        """Sets the switch to the listening's source and ticks the stem rows it hears, then waits for the sound."""
        screen = self._screen
        reconstructions = screen.reconstructions
        stems = reconstructions.stems
        label = screen.words(SOURCE_SWITCHES[listening.source])
        if reconstructions.audio_source() != label:
            reconstructions.choose_audio_source(label)
            screen.expect(reconstructions.audio_source, label.__eq__, description=f"the switch at {label}")

        for name, key in self._take.shoot.stem_keys.items():
            heard = name in listening.stems
            if stems.hears(key) != heard:
                stems.tick(key)
                screen.expect(partial(stems.hears, key), heard.__eq__, description=f"{name} heard: {heard}")

        screen.expect(screen.sound_settled, bool, description="the sound landed")
        wait_for_the_fade_to_end(screen, unfaded)

    def _boxes(self, width: int, height: int) -> List[Box]:
        """The pixels each pane of the shot stands in, with a margin around it."""
        return [
            Rect.spanning([self._camera.rect(item) for item in items]).pixel_box(MARGIN, width=width, height=height)
            for items in panes(self._screen)
        ]
