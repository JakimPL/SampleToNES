from typing import List, Tuple
from unittest.mock import Mock

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project import Project
from sampletones_core.project.instruments import Instrument, SubInstrument
from sampletones_core.utils.display import display_instrument, display_subinstrument


def _project_with_instruments(count: int) -> Tuple[Project, List[Instrument]]:
    project = Project.create()
    instruments = [Instrument(name=f"i{index}", reconstruction=Mock()) for index in range(count)]
    project.instruments.extend(instruments)
    return project, instruments


class TestDisplayInstrument:
    def test_present_shows_index(self) -> None:
        project, instruments = _project_with_instruments(3)
        assert display_instrument(project.instruments, instruments[0].id) == "00"
        assert display_instrument(project.instruments, instruments[2].id) == "02"

    def test_missing_and_none_are_placeholder(self) -> None:
        project, _ = _project_with_instruments(1)
        assert display_instrument(project.instruments, "missing") == ".."
        assert display_instrument(project.instruments, None) == ".."

    def test_index_follows_reorder(self) -> None:
        project, instruments = _project_with_instruments(3)
        first = instruments[0]
        project.instruments.append(project.instruments.pop(0))
        assert display_instrument(project.instruments, first.id) == "02"


class TestDisplaySubinstrument:
    def test_resolves_referenced_instrument(self) -> None:
        project, instruments = _project_with_instruments(2)
        subinstrument = SubInstrument(instrument_id=instruments[1].id, generator_name=GeneratorName.PULSE1)
        assert display_subinstrument(project.instruments, subinstrument) == "01"

    def test_none_is_placeholder(self) -> None:
        project, _ = _project_with_instruments(1)
        assert display_subinstrument(project.instruments, None) == ".."
