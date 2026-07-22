from sampletones_application.categories.abstract import AbstractElement


class AudioSettingsElements(AbstractElement):
    OUTPUT_DEVICE = "output_device"
    DEVICE_LABEL = "device_label"
    SAMPLE_RATE = "sample_rate"
    SAMPLE_RATE_LABEL = "sample_rate_label"
    BUFFER_SIZE = "buffer_size"
    MASTER_GAIN = "master_gain"
    MASTER_GAIN_DB = "master_gain_db"
    MASTER_GAIN_SILENT = "master_gain_silent"
    APPLY_BUTTON = "apply_button"
    REFRESH_DEVICES_BUTTON = "refresh_devices_button"
    WINDOW_TITLE = "window_title"


class ProjectPropertiesElements(AbstractElement):
    WINDOW_TITLE = "window_title"
    TITLE = "title"
    AUTHOR = "author"
    COMMENT = "comment"
    CREATED = "created"
    MODIFIED = "modified"
