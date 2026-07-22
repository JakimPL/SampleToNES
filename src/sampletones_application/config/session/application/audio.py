from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.audio import AudioDeviceManager, CurrentDevice
from sampletones_core.constants.audio import DEFAULT_BUFFER_SIZE, BufferSize
from sampletones_shared.constants.audio import (
    DEFAULT_MASTER_GAIN,
    MAX_MASTER_GAIN,
    MIN_MASTER_GAIN,
)


class AudioConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    current_device: CurrentDevice = Field(
        default_factory=CurrentDevice.default,
        description="The index of the selected audio device.",
    )
    buffer_size: BufferSize = Field(
        default=DEFAULT_BUFFER_SIZE,
        description="The audio buffer size in samples.",
    )
    master_gain: float = Field(
        default=DEFAULT_MASTER_GAIN,
        ge=MIN_MASTER_GAIN,
        le=MAX_MASTER_GAIN,
        description="The linear master playback gain applied to song playback.",
    )

    def set_audio_settings(self, audio_device_manager: AudioDeviceManager) -> None:
        self.buffer_size = audio_device_manager.buffer_size
        self.current_device = audio_device_manager.get_current_device()
