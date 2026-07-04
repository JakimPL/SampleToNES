from enum import StrEnum


class HistoryAction(StrEnum):
    """Names a single user-facing gesture recorded as one history entry.

    Each member's value doubles as the language-lookup element for the entry's
    display label, so the history panel resolves a human-readable name from the
    same enum the coordinators tag their transactions with.
    """

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
