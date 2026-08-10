from pydantic import BaseModel, Field, field_serializer

from sampletones_application.constants.playback import DEFAULT_FOLLOW_MODE, FollowMode


class PlaybackConfig(BaseModel):
    autoplay: bool = Field(
        default=True,
        description="If samples should autoplay when clicked.",
    )
    follow_mode: FollowMode = Field(
        default=DEFAULT_FOLLOW_MODE,
        description="How far the sequencer view follows the playhead during playback.",
    )
    loop_song: bool = Field(
        default=False,
        description="If the song restarts from the beginning when playback reaches the end.",
    )

    @field_serializer("follow_mode")
    def serialize_follow_mode(self, follow_mode: FollowMode) -> str:
        """Writes the mode as the plain word it names, which is what the settings file carries."""
        return follow_mode.value
