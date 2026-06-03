from sampletones_application.text.abstract import AbstractElement


class SequencerBrowserElements(AbstractElement):
    REFRESH_BUTTON = "refresh_button"
    RECONSTRUCTIONS_TREE = "reconstructions_tree"
    FILE_NOT_FOUND = "file_not_found"
    LOAD_ERROR = "load_error"
    STATUS_SEARCH = "status_search"
    LOAD_RECONSTRUCTION_DIALOG = "load_reconstruction_dialog"


class SequencerGridElements(AbstractElement):
    MODULE_OPTIONS = "module_options"
    NES_FREQUENCY = "nes_frequency"
    TEMPO = "tempo"
    SPEED = "speed"
    EXPORT_MODULE_BUTTON = "export_module_button"
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
    EXPORT_MODULE_DIALOG = "export_module_dialog"


class SequencerInstrumentsElements(AbstractElement):
    INSTRUMENTS_TEXT = "instruments_text"
    COLUMN_ID = "column_id"
    COLUMN_NAME = "column_name"
