from functools import partial
from typing import Callable, List, Optional, Sequence, Tuple

from sampletones_core.constants.enums import SpectrumMethod
from sampletones_shared.utils.text import parsed_items
from sampletones_tools.calibration.config.level import WorkingLevel
from sampletones_tools.calibration.corpus.families import Family

NamesRefusal = Callable[[str], str]


def methods_named(stated: Optional[str], default: Sequence[SpectrumMethod]) -> List[SpectrumMethod]:
    """The spectrum methods a run evaluates: the ones named, comma separated, or ``default``.

    Raises:
        ValueError: If a name is none of the spectrum methods.
    """
    known = [method.value for method in SpectrumMethod]
    return parsed_items(stated, default, parse=SpectrumMethod, refusal=_unknown("spectrum method", "methods", known))


def floats_named(stated: Optional[str], default: Sequence[float]) -> List[float]:
    """The values a sweep takes: the ones named, comma separated, or ``default``.

    Raises:
        ValueError: If a value is no number.
    """
    return parsed_items(stated, default, parse=float, refusal=lambda value: f"Not a number: {value!r}.")


def categories_named(stated: Optional[str], known: Sequence[str]) -> List[str]:
    """The categories a run measures: the ones named, comma separated, or every one ``known``.

    Raises:
        ValueError: If a name is none of the ``known`` categories.
    """
    return _names_among(stated, known, known, refusal=_unknown("category", "categories", known))


def settings_named(stated: Optional[str], default: Sequence[str], known: Sequence[str]) -> List[str]:
    """The named sets of settings a run measures beside the base: the ones named, comma separated, or ``default``.

    Raises:
        ValueError: If a name is none of the ``known`` sets.
    """
    return _names_among(stated, default, known, refusal=_unknown("set of settings", "sets", known))


def levels_named(stated: Optional[str], default: Sequence[WorkingLevel]) -> List[WorkingLevel]:
    """The levels a run matches its sounds at: the ones named, comma separated, or ``default``.

    Raises:
        ValueError: If a name is none of the levels.
    """
    known = [level.value for level in WorkingLevel]
    return parsed_items(stated, default, parse=WorkingLevel, refusal=_unknown("level", "levels", known))


def measured_categories(
    stated: Optional[str],
    skipped: Optional[str],
    catalog: Sequence[Tuple[Family, str]],
) -> List[str]:
    """The categories a run measures: those named, or every one, less those ``skipped`` leaves out.

    A skipped family leaves out every category it holds, so one name drops a whole family.

    Args:
        stated: The categories named, comma separated, or ``None`` for every one.
        skipped: The families and categories to leave out, comma separated, or ``None`` for none.
        catalog: Every category beside its family, in corpus order.

    Raises:
        ValueError: If a name is none of the categories, a skipped name none of the families or
            categories, or nothing is left to measure.
    """
    categories = [category for _, category in catalog]
    families = list(dict.fromkeys(family.value for family, _ in catalog))
    chosen = categories_named(stated, categories)
    known = [*families, *categories]
    left_out = _names_among(skipped, [], known, refusal=_unknown("family or category", "names", known))
    dropped = {category for family, category in catalog if family.value in left_out or category in left_out}
    measured = [category for category in chosen if category not in dropped]
    if not measured:
        raise ValueError("The options leave no category to measure.")

    return measured


def _names_among(
    stated: Optional[str],
    default: Sequence[str],
    known: Sequence[str],
    *,
    refusal: NamesRefusal,
) -> List[str]:
    """The names a list option states, each one of ``known``, or ``default`` where it states none."""
    return parsed_items(stated, default, parse=partial(_known_name, known), refusal=refusal)


def _known_name(known: Sequence[str], name: str) -> str:
    """``name`` itself where it is one of ``known``.

    Raises:
        ValueError: If ``name`` is none of ``known``.
    """
    if name not in known:
        raise ValueError(name)

    return name


def _unknown(kind: str, plural: str, known: Sequence[str]) -> NamesRefusal:
    """The refusal of a name that is no ``kind``, listing every one ``known`` under ``plural``."""
    listed = ", ".join(known)
    return lambda name: f"Unknown {kind} {name!r}; the {plural} are {listed}."
