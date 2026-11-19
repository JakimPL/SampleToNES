from pathlib import Path

from assets.footage.encoding import encode_command
from assets.footage.frames import FRAME_PATTERN


class TestEncodeCommand:
    def test_the_numbered_frames_play_at_the_frame_rate_beside_the_soundtrack(self) -> None:
        command = encode_command(Path("frames"), Path("sound.wav"), Path("reel.mp4"), frame_rate=60)

        assert command[command.index("-framerate") + 1] == "60"
        assert command[command.index("-framerate") + 3] == str(Path("frames") / FRAME_PATTERN)
        assert "sound.wav" in command
        assert command[-1] == "reel.mp4"

    def test_the_encoder_runs_unattended(self) -> None:
        command = encode_command(Path("frames"), Path("sound.wav"), Path("reel.mp4"), frame_rate=60)

        assert {"-nostdin", "-y"} <= set(command)
