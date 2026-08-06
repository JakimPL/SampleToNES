from sampletones_application.categories.manager import LanguageManager
from sampletones_core.utils.pitch_kind import PERIOD_VALUE_KIND, PitchValueKind


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
