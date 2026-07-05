from sampletones_application.categories.abstract import AbstractElement


class SequencerBrowserElements(AbstractElement):
    REFRESH_BUTTON = "refresh_button"
    RECONSTRUCTIONS_TREE = "reconstructions_tree"
    FILE_NOT_FOUND = "file_not_found"
    LOAD_ERROR = "load_error"
    STATUS_SEARCH = "status_search"
    LOAD_RECONSTRUCTION_DIALOG = "load_reconstruction_dialog"


class SequencerModuleElements(AbstractElement):
    MODULE_OPTIONS = "module_options"
    NES_FREQUENCY = "nes_frequency"
    ROWS = "rows"
    TEMPO = "tempo"
    SPEED = "speed"
    PROPERTIES = "properties"
    EXPORT_MODULE = "export_module"


class SequencerGridElements(AbstractElement):
    TRACKER_TEXT = "tracker_text"
    COLUMN_ROW = "column_row"
    COLUMN_SAMPLE = "column_sample"
    COLUMN_PULSE_1 = "column_pulse_1"
    COLUMN_PULSE_2 = "column_pulse_2"
    COLUMN_TRIANGLE = "column_triangle"
    COLUMN_NOISE = "column_noise"
    COLUMN_NOTE = "column_note"
    COLUMN_VOLUME = "column_volume"
    COLUMN_TRANSPOSE = "column_transpose"
    CONTEXT_PLAY = "context_play"
    CONTEXT_NOTE_OFF = "context_note_off"
    CONTEXT_SET_INSTRUMENT = "context_set_instrument"
    CONTEXT_NO_SAMPLES = "context_no_samples"
    CONTEXT_CLEAR_SUBCOLUMN = "context_clear_subcolumn"
    CONTEXT_CLEAR_CELL = "context_clear_cell"
    CONTEXT_CLEAR_ROW = "context_clear_row"
    CONTEXT_TRANSPOSE_UP = "context_transpose_up"
    CONTEXT_TRANSPOSE_DOWN = "context_transpose_down"
    CONTEXT_TRANSPOSE_OCTAVE_UP = "context_transpose_octave_up"
    CONTEXT_TRANSPOSE_OCTAVE_DOWN = "context_transpose_octave_down"
    CONTEXT_VOLUME_UP = "context_volume_up"
    CONTEXT_VOLUME_DOWN = "context_volume_down"
    CONTEXT_VOLUME_UP_COARSE = "context_volume_up_coarse"
    CONTEXT_VOLUME_DOWN_COARSE = "context_volume_down_coarse"


class SequencerOrderElements(AbstractElement):
    ORDER_TEXT = "order_text"
    ROW_MASTER = "row_master"
    ROW_PULSE_1 = "row_pulse_1"
    ROW_PULSE_2 = "row_pulse_2"
    ROW_TRIANGLE = "row_triangle"
    ROW_NOISE = "row_noise"
    CONTEXT_PLAY = "context_play"
    CONTEXT_DUPLICATE = "context_duplicate"
    CONTEXT_INSERT = "context_insert"
    CONTEXT_CLEAR = "context_clear"
    CONTEXT_REMOVE = "context_remove"
    CONTEXT_MOVE_LEFT = "context_move_left"
    CONTEXT_MOVE_RIGHT = "context_move_right"
    CONTEXT_MOVE_START = "context_move_start"
    CONTEXT_MOVE_END = "context_move_end"


class SequencerPlayerElements(AbstractElement):
    NO_SONG_LOADED = "no_song_loaded"
    POSITION = "position"
    PLAYBACK_ERROR = "playback_error"
    FOLLOW_PLAYBACK = "follow_playback"


class SequencerInstrumentsElements(AbstractElement):
    INSTRUMENTS_TEXT = "instruments_text"
    COLUMN_ID = "column_id"
    COLUMN_NAME = "column_name"
    COLUMN_LOOP = "column_loop"
    CONTEXT_EDIT = "context_edit"
    CONTEXT_RENAME = "context_rename"
    CONTEXT_DUPLICATE = "context_duplicate"
    CONTEXT_REMOVE = "context_remove"
    CONTEXT_MOVE_UP = "context_move_up"
    CONTEXT_MOVE_DOWN = "context_move_down"
    CONTEXT_MOVE_TOP = "context_move_top"
    CONTEXT_MOVE_BOTTOM = "context_move_bottom"


class SequencerHistoryElements(AbstractElement):
    HISTORY_TEXT = "history_text"
    UNDO = "undo"
    REDO = "redo"
    EMPTY = "empty"
    LOOP_ON = "loop_on"
    LOOP_OFF = "loop_off"


class SequencerHistoryActionElements(AbstractElement):
    """Display labels for history entries; values mirror ``HistoryAction`` members."""

    INITIAL = "initial"
    EDIT_ROW = "edit_row"
    NOTE_OFF = "note_off"
    CLEAR_ROW = "clear_row"
    CLEAR_SUBCOLUMN = "clear_subcolumn"
    ADJUST_TRANSPOSE = "adjust_transpose"
    ADJUST_VOLUME = "adjust_volume"
    ADD_FRAME = "add_frame"
    REMOVE_FRAME = "remove_frame"
    DUPLICATE_FRAME = "duplicate_frame"
    CLEAR_FRAME = "clear_frame"
    MOVE_FRAME = "move_frame"
    SET_ORDER_ENTRY = "set_order_entry"
    ADD_SAMPLE = "add_sample"
    REMOVE_SAMPLE = "remove_sample"
    RENAME_SAMPLE = "rename_sample"
    MOVE_SAMPLE = "move_sample"
    DUPLICATE_SAMPLE = "duplicate_sample"
    SET_SAMPLE_LOOP = "set_sample_loop"
    SET_TEMPO = "set_tempo"
    SET_SPEED = "set_speed"
    SET_NES_FREQUENCY = "set_nes_frequency"
    SET_ROWS_PER_PATTERN = "set_rows_per_pattern"
    EDIT_RECONSTRUCTION = "edit_reconstruction"
    EDIT_PROJECT_PROPERTIES = "edit_project_properties"
    UNTRACKED = "untracked"
