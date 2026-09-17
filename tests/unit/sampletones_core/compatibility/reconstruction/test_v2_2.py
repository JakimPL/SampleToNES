from typing import Any, Dict, Final

from sampletones_core.compatibility.fields import (
    APPROXIMATION,
    APPROXIMATIONS_DATA,
    ASSIGNMENTS,
    AUDIO_FILEPATH,
    BENDS,
    CHANNEL_CAP,
    CHANNEL_NAME,
    CHANNELS,
    CONFIG,
    DRIVES,
    ENTRIES,
    GENERATION,
    GENERATOR_NAME,
    GENERATORS,
    ID,
    INSTRUCTION,
    INSTRUCTIONS,
    INSTRUCTIONS_DATA,
    METADATA,
    NAME,
    ON,
    PATH,
    RECONSTRUCTION_DATA_VERSION,
    SETTINGS,
    SOURCES,
    STEM_ID,
    STEM_IDS,
    STEMS_DATA,
    UNION_DATA,
)
from sampletones_core.compatibility.reconstruction.v2_2 import SINGLE_STEM_ID, TARGET_DATA_VERSION, update
from sampletones_core.constants.algorithm import (
    ALL_STEMS_CHANNEL_CAP,
    MAX_DRIVE,
    MIN_DRIVE,
    RESTING_STEM_ID,
    UNIT_DRIVE,
)

STORED_DRIVE: Final[float] = 2.5
RECORDING: Final[str] = "/audio/kick.wav"
RECORDING_NAME: Final[str] = "kick"


def _frame(sounds: bool) -> Dict[str, Any]:
    """One frame as a stream stores it, which is the instruction tagged and nested."""
    return {"instruction_class": "PulseInstruction", INSTRUCTION: {"_type": 1, UNION_DATA: {ON: sounds}}}


def _stream(channel: str, *sounds: bool) -> Dict[str, Any]:
    return {GENERATOR_NAME: channel, INSTRUCTIONS: [_frame(value) for value in sounds]}


def _entry(upgraded: Dict[str, Any]) -> Dict[str, Any]:
    """The one recording the upgraded record answers to."""
    entry: Dict[str, Any] = upgraded[STEMS_DATA][CONFIG][ENTRIES][0]
    return entry


def _drives(upgraded: Dict[str, Any]) -> Dict[str, float]:
    drives: Dict[str, float] = _entry(upgraded)[SETTINGS][DRIVES]
    return drives


def _owners(upgraded: Dict[str, Any]) -> Any:
    return upgraded[STEMS_DATA][ASSIGNMENTS]


class TestTheAudioAFileNoLongerCarries:
    """A reconstruction renders its channels from what it stores, so the stored waveform goes."""

    def test_the_mixed_audio_is_let_go_of(self) -> None:
        data = {APPROXIMATION: [0.0, 1.0]}

        assert APPROXIMATION not in update(data)

    def test_the_audio_each_channel_rendered_is_let_go_of(self) -> None:
        data = {APPROXIMATIONS_DATA: [{GENERATOR_NAME: "pulse1", APPROXIMATION: [0.0]}]}

        assert APPROXIMATIONS_DATA not in update(data)


class TestWhatNamesAStream:
    """A stream was keyed by the generator that played it, and is keyed by its channel now."""

    def test_a_stream_reads_as_its_channel(self) -> None:
        upgraded = update({INSTRUCTIONS_DATA: [_stream("pulse1", True)]})

        assert upgraded[INSTRUCTIONS_DATA][0][CHANNEL_NAME] == "pulse1"
        assert GENERATOR_NAME not in upgraded[INSTRUCTIONS_DATA][0]


class TestTheVersionTheEmbeddedConfigStates:
    """A reconstruction carries the configuration it was built under, metadata and all."""

    def test_the_embedded_metadata_states_the_version_reached(self) -> None:
        data = {CONFIG: {METADATA: {RECONSTRUCTION_DATA_VERSION: "2.1"}}}

        upgraded = update(data)

        assert upgraded[CONFIG][METADATA][RECONSTRUCTION_DATA_VERSION] == TARGET_DATA_VERSION

    def test_a_config_stating_no_metadata_gains_none(self) -> None:
        data = {CONFIG: {GENERATION: {GENERATORS: ["pulse1"]}}}

        assert METADATA not in update(data)[CONFIG]


class TestTheRecordingTheRecordAnswersTo:
    """The channels a run handed out and the level it drove them at move onto the recording."""

    def test_the_channels_the_run_handed_out_reach_the_recording(self) -> None:
        data = {CONFIG: {GENERATION: {GENERATORS: ["pulse1", "noise"]}}}

        assert _entry(update(data)) == {
            ID: SINGLE_STEM_ID,
            SETTINGS: {
                CHANNELS: ["pulse1", "noise"],
                BENDS: [],
                DRIVES: {"pulse1": UNIT_DRIVE, "noise": UNIT_DRIVE},
                CHANNEL_CAP: ALL_STEMS_CHANNEL_CAP,
            },
        }

    def test_the_stored_drive_reaches_every_channel(self) -> None:
        data = {CONFIG: {GENERATION: {GENERATORS: ["pulse1", "noise"], "drive": STORED_DRIVE}}}

        assert _drives(update(data)) == {"pulse1": STORED_DRIVE, "noise": STORED_DRIVE}

    def test_a_drive_stored_under_its_older_name_is_read(self) -> None:
        data = {CONFIG: {GENERATION: {GENERATORS: ["pulse1"], "mixer": STORED_DRIVE}}}

        assert _drives(update(data)) == {"pulse1": STORED_DRIVE}

    def test_a_run_stating_no_drive_played_at_unit(self) -> None:
        data = {CONFIG: {GENERATION: {GENERATORS: ["pulse1"]}}}

        assert _drives(update(data)) == {"pulse1": UNIT_DRIVE}

    def test_a_drive_outside_the_bounds_is_held_within_them(self) -> None:
        quiet = {CONFIG: {GENERATION: {GENERATORS: ["pulse1"], "drive": MIN_DRIVE / 2}}}
        loud = {CONFIG: {GENERATION: {GENERATORS: ["pulse1"], "drive": MAX_DRIVE * 2}}}

        assert _drives(update(quiet)) == {"pulse1": MIN_DRIVE}
        assert _drives(update(loud)) == {"pulse1": MAX_DRIVE}


class TestWhereTheRecordingCameFrom:
    """The file a conversion read moves onto the record, which is where a document keeps it."""

    def test_the_stated_file_becomes_the_recordings_source(self) -> None:
        upgraded = update({AUDIO_FILEPATH: RECORDING})

        assert upgraded[STEMS_DATA][SOURCES] == [{STEM_ID: SINGLE_STEM_ID, NAME: RECORDING_NAME, PATH: RECORDING}]

    def test_a_file_naming_no_recording_records_no_source(self) -> None:
        """A document detached from its origin names none, which a stored project carries."""
        assert update({})[STEMS_DATA][SOURCES] == []

    def test_the_key_the_record_replaces_is_let_go_of(self) -> None:
        assert AUDIO_FILEPATH not in update({AUDIO_FILEPATH: RECORDING})[STEMS_DATA]


class TestWhoHoldsEachFrame:
    """Rest and silence name the same frames, so the owners are read from the stream itself."""

    def test_a_sounding_frame_answers_to_the_recording(self) -> None:
        upgraded = update({INSTRUCTIONS_DATA: [_stream("pulse1", True, True)]})

        assert _owners(upgraded) == [{CHANNEL_NAME: "pulse1", STEM_IDS: [SINGLE_STEM_ID, SINGLE_STEM_ID]}]

    def test_a_silent_frame_answers_to_rest(self) -> None:
        upgraded = update({INSTRUCTIONS_DATA: [_stream("pulse1", True, False, True)]})

        assert _owners(upgraded) == [
            {CHANNEL_NAME: "pulse1", STEM_IDS: [SINGLE_STEM_ID, RESTING_STEM_ID, SINGLE_STEM_ID]}
        ]

    def test_a_channel_holding_no_frame_names_no_owner(self) -> None:
        data = {INSTRUCTIONS_DATA: [_stream("pulse1", True), _stream("noise")]}

        assert _owners(update(data)) == [{CHANNEL_NAME: "pulse1", STEM_IDS: [SINGLE_STEM_ID]}]

    def test_a_frame_stating_nothing_reads_as_silent(self) -> None:
        """A payload this build cannot read a flag from describes no sound, so nothing holds it."""
        data = {INSTRUCTIONS_DATA: [{GENERATOR_NAME: "pulse1", INSTRUCTIONS: ["frame"]}]}

        assert _owners(update(data)) == [{CHANNEL_NAME: "pulse1", STEM_IDS: [RESTING_STEM_ID]}]


class TestWhatTheStepLeavesAlone:
    """The payload handed in stands as it was, and what the step knows nothing of travels."""

    def test_the_payload_handed_in_is_left_untouched(self) -> None:
        data = {
            APPROXIMATIONS_DATA: [{GENERATOR_NAME: "pulse1"}],
            INSTRUCTIONS_DATA: [_stream("pulse1", True)],
        }

        update(data)

        assert APPROXIMATIONS_DATA in data
        assert data[INSTRUCTIONS_DATA][0][GENERATOR_NAME] == "pulse1"

    def test_a_payload_naming_no_known_section_still_gains_a_record(self) -> None:
        upgraded = update({ID: "abc"})

        assert upgraded[ID] == "abc"
        assert _entry(upgraded)[SETTINGS][CHANNELS] == []
        assert _owners(upgraded) == []
