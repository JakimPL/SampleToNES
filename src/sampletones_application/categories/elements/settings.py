from sampletones_application.categories.abstract import AbstractElement


class AudioSettingsElements(AbstractElement):
    OUTPUT_DEVICE = "output_device"
    SAMPLE_RATE = "sample_rate"
    BUFFER_SIZE = "buffer_size"
    APPLY_BUTTON = "apply_button"
    REFRESH_DEVICES_BUTTON = "refresh_devices_button"
    WINDOW_TITLE = "window_title"
