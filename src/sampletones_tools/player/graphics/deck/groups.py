from dataclasses import dataclass
from typing import Final

BAR_GROUP: Final[str] = "bar"
CHROME_GROUP: Final[str] = "chrome"
PROGRESS_GROUP: Final[str] = "progress"
PULSE_WAVE_GROUP: Final[str] = "wave_pulse"
OTHER_WAVE_GROUP: Final[str] = "wave_other"
PULSE_METER_GROUP: Final[str] = "meter_pulse"
OTHER_METER_GROUP: Final[str] = "meter_other"
FIRST_PIN_GROUP: Final[str] = "pin_first"
SECOND_PIN_GROUP: Final[str] = "pin_second"


@dataclass(frozen=True)
class TileName:
    """A background tile, named by its group and its member there."""

    group: str
    member: str
