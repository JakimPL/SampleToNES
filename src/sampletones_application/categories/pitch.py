from dataclasses import dataclass
from typing import Self

from sampletones_application.categories.manager import LanguageManager
from sampletones_core.utils.pitch_kind import (
    PERIOD_VALUE_KIND,
    PITCH_VALUE_KIND,
    PitchValueKind,
)


@dataclass(frozen=True)
class PitchTooltips:
    """A pitch stepper's help in both readings, so a panel resolves the one its field takes.

    A stepper states a pitch on the tonal channels and a period on the noise channel, and a panel
    holding steppers of both kinds phrases each from the same template. Building the pair together
    keeps the two readings in step and leaves the choice to the moment a field is drawn.

    Attributes:
        pitch: The help a stepper reading a pitch shows.
        period: The help a stepper reading a period shows.
    """

    pitch: str
    period: str

    @classmethod
    def build(
        cls,
        language_manager: LanguageManager,
        template: str,
    ) -> Self:
        """Phrases both readings from one template.

        Args:
            language_manager: Where the example note name and value are read from.
            template: The panel's own surrounding wording.

        Returns:
            PitchTooltips: The help in both readings.
        """
        return cls(
            pitch=cls.build_pitch_tooltip(
                language_manager,
                PITCH_VALUE_KIND,
                template,
            ),
            period=cls.build_pitch_tooltip(
                language_manager,
                PERIOD_VALUE_KIND,
                template,
            ),
        )

    def for_kind(self, kind: PitchValueKind) -> str:
        """The help a stepper of ``kind`` shows."""
        return self.period if kind is PERIOD_VALUE_KIND else self.pitch

    @staticmethod
    def build_pitch_tooltip(
        language_manager: LanguageManager,
        kind: PitchValueKind,
        template: str,
    ) -> str:
        """Fills a pitch stepper's help template with the shared example for ``kind``: the quantity's name
        ("pitch" or "period"), an example note name, and the matching numeric value. The value is resolved
        from the example name through the kind itself, so the name and value the tooltip shows always agree.
        Both the reconstruction and instruction steppers compose their tooltips through here, keeping one
        definition of the example while each supplies its own surrounding wording via ``template``."""
        is_period = kind is PERIOD_VALUE_KIND
        type_name = language_manager["global.pitch.label.period_name" if is_period else "global.pitch.label.pitch_name"]
        example_name = language_manager[
            "global.pitch.label.period_example" if is_period else "global.pitch.label.pitch_example"
        ]
        example_value = kind.from_text(example_name, kind.minimum)
        return template.format(type_name, example_name, example_value)
