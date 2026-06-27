from sampletones_core.library.filename.utils import get_display_name_from_key
from sampletones_core.library.key import InstructionLibraryKey

HASH = "6c2f0b1f03cdc2dff8c4ed808b4d2864"


def make_key(*, sample_rate: int, frame_length: int, transformation_gamma: int) -> InstructionLibraryKey:
    return InstructionLibraryKey(
        sample_rate=sample_rate,
        frame_length=frame_length,
        window_size=2 * frame_length,
        transformation_gamma=transformation_gamma,
        config_hash=HASH,
        filename=f"library_{HASH}",
    )


class TestGetDisplayNameFromKey:
    def test_renders_compact_friendly_name(self) -> None:
        key = make_key(sample_rate=44100, frame_length=1470, transformation_gamma=100)

        assert get_display_name_from_key(key) == "44.1 kHz · 30 Hz · γ100"

    def test_derives_nes_frequency_from_frame_length(self) -> None:
        key = make_key(sample_rate=48000, frame_length=800, transformation_gamma=0)

        assert get_display_name_from_key(key) == "48 kHz · 60 Hz · γ0"
