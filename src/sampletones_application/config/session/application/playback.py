from pydantic import BaseModel, Field


class PlaybackConfig(BaseModel):
    autoplay: bool = Field(
        default=True,
        description="If samples should autoplay when clicked.",
    )
    follow_playback: bool = Field(
        default=True,
        description="If the sequencer tracker follows the playhead during playback.",
    )
    loop_song: bool = Field(
        default=False,
        description="If the song restarts from the beginning when playback reaches the end.",
    )
