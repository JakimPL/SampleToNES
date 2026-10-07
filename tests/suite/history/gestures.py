from collections.abc import Hashable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Callable, Dict, Final, Optional, Tuple

from sampletones_application.constants.instruments import INSTRUMENT_CHANNEL
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.reconstruction.rewrites.steps import StemRemovalRequest
from sampletones_application.ui.panels.sequencer.module import GUISequencerModulePanel
from sampletones_application.ui.panels.sequencer.order.panel import GUISequencerOrderPanel
from sampletones_application.ui.panels.sequencer.tracker.panel import GUISequencerTrackerPanel
from sampletones_application.ui.panels.sequencer.voices.panel import GUISequencerVoicesPanel
from sampletones_application.view_model.sequencer.region import OrderCell, OrderRegion, TrackerCell, TrackerRegion
from sampletones_application.view_model.sequencer.slot import SUBCOLUMNS, column_slot_base
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.features.envelope import Envelope
from sampletones_core.project.patterns.pitch import Note, Step
from tests.suite.history.projects import BASS, LEAD, PAD, PLUCK
from tests.suite.history.session import HistorySession
from tests.suite.sequencer import sample_reconstruction
from tests.suite.stems import STEM_B_ID, recorded_from

FIRST_FRAME: Final[int] = 0
SECOND_FRAME: Final[int] = 1
MODULE_TARGET: Final[Tuple[()]] = ()
ARRIVING_SAMPLE: Final[str] = "arriving.stn"
ARRIVING_RECORDINGS: Final[Tuple[Path, Path]] = (Path("arriving-a.wav"), Path("arriving-b.wav"))
RETUNED_RATE: Final[int] = 50
RETUNED_AGAIN_RATE: Final[int] = 48
EDITED_ENVELOPE: Final[Envelope[int]] = Envelope[int](items=(11, 9, 7))
EDITED_REFERENCE: Final[int] = 64
REMOVED_STEM_NAME: Final[str] = "b"

Target = Optional[Hashable]


class Part(StrEnum):
    """The parts of a project a gesture changes, each the unit an entry owns for it."""

    SONG_CELLS = "song cells"
    ORDER = "order"
    PATTERN_LENGTH = "pattern length"
    VOICES = "voices"
    INSTRUMENT = "instrument"
    RECONSTRUCTION_CHANNEL = "reconstruction channel"
    STEMS = "stems"
    RATE = "rate"
    SETTINGS = "settings"
    PROPERTIES = "properties"


@dataclass(frozen=True)
class Gesture:
    """One user gesture, run through the hook its panel calls.

    ``target`` names what the gesture changes the way the history's coalescing reads it, worked
    out before the gesture runs, so two gestures of one action and one target in a row make one
    entry. ``prepare`` runs first and records nothing: opening a voice on the Reconstructions tab,
    copying a block.
    """

    label: str
    action: HistoryAction
    part: Part
    run: Callable[[HistorySession], None]
    target: Callable[[HistorySession], Target]
    prepare: Callable[[HistorySession], None]


def _nothing(_session: HistorySession) -> None:
    return None


def _untargeted(_session: HistorySession) -> Target:
    return None


def _module_target(_session: HistorySession) -> Target:
    return MODULE_TARGET


def _cell_target(
    channel: ChannelName,
    row: int,
) -> Callable[[HistorySession], Target]:
    def target(session: HistorySession) -> Target:
        return (session.sequencer._sequencer_tracker_logic.frame_index, channel, row)

    return target


def _edit_row_target(
    channel: ChannelName,
    row: int,
    *,
    voice: bool,
    pitch: bool,
    volume: bool,
) -> Callable[[HistorySession], Target]:
    def target(session: HistorySession) -> Target:
        return (session.sequencer._sequencer_tracker_logic.frame_index, channel, row, voice, pitch, volume)

    return target


def _cell_region(
    channel: ChannelName,
    first_row: int,
    last_row: int,
) -> TrackerRegion:
    base = column_slot_base(channel)
    return TrackerRegion(
        first_row=first_row,
        last_row=last_row,
        first_slot=base,
        last_slot=base + len(SUBCOLUMNS) - 1,
    )


LEAD_REGION: Final[TrackerRegion] = _cell_region(ChannelName.PULSE1, 0, 2)
ORDER_REGION: Final[OrderRegion] = OrderRegion(first_row=1, last_row=2, first_position=0, last_position=0)


def _adjustment_target(region: TrackerRegion) -> Callable[[HistorySession], Target]:
    def target(session: HistorySession) -> Target:
        frame = session.sequencer._sequencer_tracker_logic.frame_index
        return (frame, region.first_row, region.last_row, region.first_slot, region.last_slot)

    return target


def _voice_target(name: str) -> Callable[[HistorySession], Target]:
    def target(session: HistorySession) -> Target:
        return (session.voice_id(name),)

    return target


def _instrument_target(
    name: str,
    feature_key: FeatureKey,
) -> Callable[[HistorySession], Target]:
    def target(session: HistorySession) -> Target:
        return (session.voice_id(name), feature_key)

    return target


def _opening(name: str) -> Callable[[HistorySession], None]:
    def prepare(session: HistorySession) -> None:
        session.open_voice(name)

    return prepare


def write_arriving_sample(session: HistorySession) -> Path:
    """Writes a document beside the project, the file an Add or a Replace from the browser reads."""
    path = session.project_file.parent / ARRIVING_SAMPLE
    recorded_from(sample_reconstruction([ChannelName.PULSE2]), ARRIVING_RECORDINGS).save(path)
    return path


def _tracker(session: HistorySession) -> GUISequencerTrackerPanel:
    return session.sequencer._sequencer_tracker_panel


def _order(session: HistorySession) -> GUISequencerOrderPanel:
    return session.sequencer._sequencer_order_panel


def _module(session: HistorySession) -> GUISequencerModulePanel:
    return session.sequencer._sequencer_module_panel


def _voices(session: HistorySession) -> GUISequencerVoicesPanel:
    return session.sequencer._sequencer_voices_panel


def _type_a_sample_note(session: HistorySession) -> None:
    _tracker(session).on_set_row(1, ChannelName.PULSE1, session.voice_id(LEAD), Note(value=62), None)


def _type_an_instrument_note(session: HistorySession) -> None:
    _tracker(session).on_set_row(3, ChannelName.PULSE2, session.voice_id(PAD), Note(value=65), 7)


def _type_a_volume(session: HistorySession) -> None:
    _tracker(session).on_set_row(0, ChannelName.PULSE1, None, None, 5)


def _type_a_step(session: HistorySession) -> None:
    _tracker(session).on_set_row(2, ChannelName.TRIANGLE, None, Step(value=-3), None)


def _cut_a_note(session: HistorySession) -> None:
    _tracker(session).on_set_note_off(1, ChannelName.PULSE2)


def _clear_a_row(session: HistorySession) -> None:
    _tracker(session).on_clear_row(0, ChannelName.PULSE1)


def _clear_a_volume(session: HistorySession) -> None:
    _tracker(session).on_clear_subcolumn(0, ChannelName.PULSE1, SubColumn.VOLUME)


def _transpose_a_block(session: HistorySession) -> None:
    _tracker(session).on_adjust_transpose(LEAD_REGION, 1)


def _quiet_a_block(session: HistorySession) -> None:
    _tracker(session).on_adjust_volume(LEAD_REGION, -1)


def _cut_a_tracker_block(session: HistorySession) -> None:
    _tracker(session).on_cut_block(LEAD_REGION)


def _delete_a_tracker_block(session: HistorySession) -> None:
    _tracker(session).on_delete_block(LEAD_REGION)


def _copy_a_tracker_block(session: HistorySession) -> None:
    _tracker(session).on_copy_block(LEAD_REGION)


def _paste_a_tracker_block(session: HistorySession) -> None:
    _tracker(session).on_paste_block(TrackerCell(row=4, channel=ChannelName.PULSE2))


def _insert_a_frame(session: HistorySession) -> None:
    _order(session).on_insert_requested(SECOND_FRAME)


def _remove_a_frame(session: HistorySession) -> None:
    _order(session).on_remove_requested(SECOND_FRAME)


def _duplicate_a_frame(session: HistorySession) -> None:
    _order(session).on_duplicate_requested(FIRST_FRAME)


def _clone_a_frame(session: HistorySession) -> None:
    _order(session).on_clone_requested(FIRST_FRAME)


def _clear_a_frame(session: HistorySession) -> None:
    _order(session).on_clear_requested(SECOND_FRAME)


def _move_a_frame(session: HistorySession) -> None:
    _order(session).on_move_requested(SECOND_FRAME, FIRST_FRAME)


def _set_an_order_entry(session: HistorySession) -> None:
    _order(session).on_set_order_entry(ChannelName.PULSE1, FIRST_FRAME, 1)


def _set_a_master_entry(session: HistorySession) -> None:
    _order(session).on_set_master_entry(SECOND_FRAME, 0)


def _cut_an_order_block(session: HistorySession) -> None:
    _order(session).on_cut_block(ORDER_REGION)


def _delete_an_order_block(session: HistorySession) -> None:
    _order(session).on_delete_block(ORDER_REGION)


def _copy_an_order_block(session: HistorySession) -> None:
    _order(session).on_copy_block(ORDER_REGION)


def _paste_an_order_block(session: HistorySession) -> None:
    _order(session).on_paste_block(OrderCell(channel=ChannelName.TRIANGLE, position=SECOND_FRAME))


def _lengthen_patterns(session: HistorySession) -> None:
    _module(session).on_rows_per_pattern(12)


def _shorten_patterns(session: HistorySession) -> None:
    _module(session).on_rows_per_pattern(4)


def _set_the_tempo(session: HistorySession) -> None:
    _module(session).on_tempo(120)


def _set_the_speed(session: HistorySession) -> None:
    _module(session).on_speed(3)


def _edit_the_properties(session: HistorySession) -> None:
    info = session.project.info
    settings = session.project.settings
    session.app.project_properties_window.on_commit(
        f"{info.title} again",
        info.author,
        info.comment,
        settings.first_highlight + 1,
        settings.second_highlight,
    )


def _add_a_sample(session: HistorySession) -> None:
    session.sequencer.import_reconstruction(write_arriving_sample(session))


def _replace_a_sample(session: HistorySession) -> None:
    session.mark_voice(BASS)
    session.sequencer.replace_reconstruction(write_arriving_sample(session))


def _add_an_instrument(session: HistorySession) -> None:
    _voices(session).on_new_instrument_requested()


def _take_a_channel(session: HistorySession) -> None:
    _voices(session).on_instrument_from_channel_requested(session.voice_id(LEAD), ChannelName.PULSE1)


def _renaming(name: str) -> Callable[[HistorySession], None]:
    def run(session: HistorySession) -> None:
        _voices(session).on_rename_committed(session.voice_id(name), f"{name} again")

    return run


def _moving(name: str) -> Callable[[HistorySession], None]:
    def run(session: HistorySession) -> None:
        _voices(session).on_move_requested(session.voice_id(name), len(session.project.voices) - 1)

    return run


def _duplicating(name: str) -> Callable[[HistorySession], None]:
    def run(session: HistorySession) -> None:
        _voices(session).on_duplicate_requested(session.voice_id(name))

    return run


def _removing(name: str) -> Callable[[HistorySession], None]:
    def run(session: HistorySession) -> None:
        _voices(session).on_remove_requested(session.voice_id(name))

    return run


def _edit_an_instrument_envelope(session: HistorySession) -> None:
    session.instruments.handle_envelope_changed(INSTRUMENT_CHANNEL, FeatureKey.VOLUME, EDITED_ENVELOPE)


def _edit_a_channel_envelope(session: HistorySession) -> None:
    session.instruments.handle_envelope_changed(ChannelName.PULSE1, FeatureKey.VOLUME, EDITED_ENVELOPE)


def _move_a_channel_reference(session: HistorySession) -> None:
    session.instruments.handle_pitch_value_changed(ChannelName.PULSE1, EDITED_REFERENCE)


def _remove_a_recording(session: HistorySession) -> None:
    session.app._reconstruction_coordinator.request_rewrite(
        StemRemovalRequest(stem_id=STEM_B_ID, stem_name=REMOVED_STEM_NAME)
    )


def _retune_the_project(session: HistorySession) -> None:
    session.sequencer._nes_frequency_change_acknowledged = True
    _module(session).on_nes_frequency(RETUNED_RATE)


def _rate_target(_session: HistorySession) -> Target:
    return (RETUNED_RATE,)


def _retune_the_project_again(session: HistorySession) -> None:
    session.sequencer._nes_frequency_change_acknowledged = True
    _module(session).on_nes_frequency(RETUNED_AGAIN_RATE)


def _rate_again_target(_session: HistorySession) -> Target:
    return (RETUNED_AGAIN_RATE,)


def _gesture(
    label: str,
    action: HistoryAction,
    part: Part,
    run: Callable[[HistorySession], None],
    *,
    target: Callable[[HistorySession], Target] = _untargeted,
    prepare: Callable[[HistorySession], None] = _nothing,
) -> Gesture:
    return Gesture(label=label, action=action, part=part, run=run, target=target, prepare=prepare)


GESTURES: Final[Tuple[Gesture, ...]] = (
    _gesture(
        "type a note with a sample",
        HistoryAction.EDIT_ROW,
        Part.SONG_CELLS,
        _type_a_sample_note,
        target=_edit_row_target(ChannelName.PULSE1, 1, voice=True, pitch=True, volume=False),
    ),
    _gesture(
        "type a note with an instrument",
        HistoryAction.EDIT_ROW,
        Part.SONG_CELLS,
        _type_an_instrument_note,
        target=_edit_row_target(ChannelName.PULSE2, 3, voice=True, pitch=True, volume=True),
    ),
    _gesture(
        "type a volume",
        HistoryAction.EDIT_ROW,
        Part.SONG_CELLS,
        _type_a_volume,
        target=_edit_row_target(ChannelName.PULSE1, 0, voice=False, pitch=False, volume=True),
    ),
    _gesture(
        "type a step",
        HistoryAction.EDIT_ROW,
        Part.SONG_CELLS,
        _type_a_step,
        target=_edit_row_target(ChannelName.TRIANGLE, 2, voice=False, pitch=True, volume=False),
    ),
    _gesture(
        "cut a note",
        HistoryAction.NOTE_OFF,
        Part.SONG_CELLS,
        _cut_a_note,
        target=_cell_target(ChannelName.PULSE2, 1),
    ),
    _gesture("clear a row", HistoryAction.CLEAR_ROW, Part.SONG_CELLS, _clear_a_row),
    _gesture("clear a volume", HistoryAction.CLEAR_SUBCOLUMN, Part.SONG_CELLS, _clear_a_volume),
    _gesture(
        "transpose a block",
        HistoryAction.ADJUST_TRANSPOSE,
        Part.SONG_CELLS,
        _transpose_a_block,
        target=_adjustment_target(LEAD_REGION),
    ),
    _gesture(
        "quiet a block",
        HistoryAction.ADJUST_VOLUME,
        Part.SONG_CELLS,
        _quiet_a_block,
        target=_adjustment_target(LEAD_REGION),
    ),
    _gesture("cut a tracker block", HistoryAction.CUT_BLOCK, Part.SONG_CELLS, _cut_a_tracker_block),
    _gesture("delete a tracker block", HistoryAction.DELETE_BLOCK, Part.SONG_CELLS, _delete_a_tracker_block),
    _gesture(
        "paste a tracker block",
        HistoryAction.PASTE_BLOCK,
        Part.SONG_CELLS,
        _paste_a_tracker_block,
        prepare=_copy_a_tracker_block,
    ),
    _gesture("insert a frame", HistoryAction.ADD_FRAME, Part.ORDER, _insert_a_frame),
    _gesture("remove a frame", HistoryAction.REMOVE_FRAME, Part.ORDER, _remove_a_frame),
    _gesture("duplicate a frame", HistoryAction.DUPLICATE_FRAME, Part.ORDER, _duplicate_a_frame),
    _gesture("clone a frame", HistoryAction.CLONE_FRAME, Part.ORDER, _clone_a_frame),
    _gesture("clear a frame", HistoryAction.CLEAR_FRAME, Part.ORDER, _clear_a_frame),
    _gesture("move a frame", HistoryAction.MOVE_FRAME, Part.ORDER, _move_a_frame),
    _gesture("set an order entry", HistoryAction.SET_ORDER_ENTRY, Part.ORDER, _set_an_order_entry),
    _gesture("set a master entry", HistoryAction.SET_ORDER_ENTRY, Part.ORDER, _set_a_master_entry),
    _gesture("cut an order block", HistoryAction.CUT_BLOCK, Part.ORDER, _cut_an_order_block),
    _gesture("delete an order block", HistoryAction.DELETE_BLOCK, Part.ORDER, _delete_an_order_block),
    _gesture(
        "paste an order block",
        HistoryAction.PASTE_BLOCK,
        Part.ORDER,
        _paste_an_order_block,
        prepare=_copy_an_order_block,
    ),
    _gesture(
        "lengthen the patterns",
        HistoryAction.SET_ROWS_PER_PATTERN,
        Part.PATTERN_LENGTH,
        _lengthen_patterns,
        target=_module_target,
    ),
    _gesture(
        "shorten the patterns",
        HistoryAction.SET_ROWS_PER_PATTERN,
        Part.PATTERN_LENGTH,
        _shorten_patterns,
        target=_module_target,
    ),
    _gesture("set the tempo", HistoryAction.SET_TEMPO, Part.SETTINGS, _set_the_tempo, target=_module_target),
    _gesture("set the speed", HistoryAction.SET_SPEED, Part.SETTINGS, _set_the_speed, target=_module_target),
    _gesture(
        "edit the properties",
        HistoryAction.EDIT_PROJECT_PROPERTIES,
        Part.PROPERTIES,
        _edit_the_properties,
    ),
    _gesture("add a sample", HistoryAction.ADD_SAMPLE, Part.VOICES, _add_a_sample),
    _gesture("replace a sample", HistoryAction.REPLACE_SAMPLE, Part.VOICES, _replace_a_sample),
    _gesture("add an instrument", HistoryAction.ADD_INSTRUMENT, Part.VOICES, _add_an_instrument),
    _gesture("take a channel as an instrument", HistoryAction.ADD_INSTRUMENT, Part.VOICES, _take_a_channel),
    _gesture("rename a sample", HistoryAction.RENAME_VOICE, Part.VOICES, _renaming(LEAD)),
    _gesture("rename an instrument", HistoryAction.RENAME_VOICE, Part.VOICES, _renaming(PAD)),
    _gesture("move a sample", HistoryAction.MOVE_VOICE, Part.VOICES, _moving(LEAD)),
    _gesture("move an instrument", HistoryAction.MOVE_VOICE, Part.VOICES, _moving(PAD)),
    _gesture("duplicate a sample", HistoryAction.DUPLICATE_VOICE, Part.VOICES, _duplicating(BASS)),
    _gesture("duplicate an instrument", HistoryAction.DUPLICATE_VOICE, Part.VOICES, _duplicating(PLUCK)),
    _gesture("remove a sample", HistoryAction.REMOVE_VOICE, Part.VOICES, _removing(LEAD)),
    _gesture("remove an instrument", HistoryAction.REMOVE_VOICE, Part.VOICES, _removing(PAD)),
    _gesture("remove another instrument", HistoryAction.REMOVE_VOICE, Part.VOICES, _removing(PLUCK)),
    _gesture(
        "edit an instrument's envelope",
        HistoryAction.EDIT_INSTRUMENT,
        Part.INSTRUMENT,
        _edit_an_instrument_envelope,
        target=_instrument_target(PAD, FeatureKey.VOLUME),
        prepare=_opening(PAD),
    ),
    _gesture(
        "edit a channel's envelope",
        HistoryAction.EDIT_RECONSTRUCTION,
        Part.RECONSTRUCTION_CHANNEL,
        _edit_a_channel_envelope,
        target=_voice_target(LEAD),
        prepare=_opening(LEAD),
    ),
    _gesture(
        "move a channel's reference",
        HistoryAction.EDIT_RECONSTRUCTION,
        Part.RECONSTRUCTION_CHANNEL,
        _move_a_channel_reference,
        target=_voice_target(LEAD),
        prepare=_opening(LEAD),
    ),
    _gesture(
        "remove a recording",
        HistoryAction.EDIT_RECONSTRUCTION,
        Part.STEMS,
        _remove_a_recording,
        prepare=_opening(LEAD),
    ),
    _gesture(
        "retune the project",
        HistoryAction.SET_NES_FREQUENCY,
        Part.RATE,
        _retune_the_project,
        target=_rate_target,
    ),
    _gesture(
        "retune the project again",
        HistoryAction.SET_NES_FREQUENCY,
        Part.RATE,
        _retune_the_project_again,
        target=_rate_again_target,
    ),
    _gesture(
        "retune the project with a sample open",
        HistoryAction.SET_NES_FREQUENCY,
        Part.RATE,
        _retune_the_project,
        target=_rate_target,
        prepare=_opening(LEAD),
    ),
)

GESTURES_BY_LABEL: Final[Dict[str, Gesture]] = {gesture.label: gesture for gesture in GESTURES}


def perform(
    session: HistorySession,
    gesture: Gesture,
) -> None:
    """Prepares a gesture, then runs it under the audit, which checks the one entry it records."""
    gesture.prepare(session)
    target = gesture.target(session)
    session.audit.perform(lambda: gesture.run(session), action=gesture.action, target=target)


PAIR_KINDS: Final[Dict[HistoryAction, Tuple[str, str]]] = {
    HistoryAction.EDIT_ROW: ("type a note with a sample", "type a note with a sample"),
    HistoryAction.NOTE_OFF: ("cut a note", "cut a note"),
    HistoryAction.CLEAR_ROW: ("clear a row", "clear a row"),
    HistoryAction.CLEAR_SUBCOLUMN: ("clear a volume", "clear a volume"),
    HistoryAction.ADJUST_TRANSPOSE: ("transpose a block", "transpose a block"),
    HistoryAction.ADJUST_VOLUME: ("quiet a block", "quiet a block"),
    HistoryAction.CUT_BLOCK: ("cut a tracker block", "cut an order block"),
    HistoryAction.DELETE_BLOCK: ("delete an order block", "delete a tracker block"),
    HistoryAction.PASTE_BLOCK: ("paste a tracker block", "paste an order block"),
    HistoryAction.ADD_FRAME: ("insert a frame", "insert a frame"),
    HistoryAction.REMOVE_FRAME: ("remove a frame", "remove a frame"),
    HistoryAction.DUPLICATE_FRAME: ("duplicate a frame", "duplicate a frame"),
    HistoryAction.CLONE_FRAME: ("clone a frame", "clone a frame"),
    HistoryAction.CLEAR_FRAME: ("clear a frame", "clear a frame"),
    HistoryAction.MOVE_FRAME: ("move a frame", "move a frame"),
    HistoryAction.SET_ORDER_ENTRY: ("set an order entry", "set a master entry"),
    HistoryAction.SET_ROWS_PER_PATTERN: ("lengthen the patterns", "shorten the patterns"),
    HistoryAction.SET_TEMPO: ("set the tempo", "set the tempo"),
    HistoryAction.SET_SPEED: ("set the speed", "set the speed"),
    HistoryAction.EDIT_PROJECT_PROPERTIES: ("edit the properties", "edit the properties"),
    HistoryAction.ADD_SAMPLE: ("add a sample", "add a sample"),
    HistoryAction.REPLACE_SAMPLE: ("replace a sample", "replace a sample"),
    HistoryAction.ADD_INSTRUMENT: ("add an instrument", "take a channel as an instrument"),
    HistoryAction.RENAME_VOICE: ("rename an instrument", "rename a sample"),
    HistoryAction.MOVE_VOICE: ("move a sample", "move an instrument"),
    HistoryAction.DUPLICATE_VOICE: ("duplicate a sample", "duplicate an instrument"),
    HistoryAction.REMOVE_VOICE: ("remove another instrument", "remove an instrument"),
    HistoryAction.EDIT_INSTRUMENT: ("edit an instrument's envelope", "edit an instrument's envelope"),
    HistoryAction.EDIT_RECONSTRUCTION: ("edit a channel's envelope", "move a channel's reference"),
    HistoryAction.SET_NES_FREQUENCY: ("retune the project", "retune the project again"),
}


def attempt(
    session: HistorySession,
    gesture: Gesture,
) -> None:
    """Prepares a gesture and runs it under the audit, which takes a gesture left nothing to change as none."""
    gesture.prepare(session)
    target = gesture.target(session)
    session.audit.attempt(lambda: gesture.run(session), action=gesture.action, target=target)
