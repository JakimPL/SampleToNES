from typing import Final, List, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.ui.panels.instruction.library import GUIInstructionsLibraryPanel
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.library import InstructionLibraryKey
from sampletones_core.structures.tree import GeneratorNode, LibraryNode
from tests.suite.language import FakeLanguageManager

STATUS_KEY: Final[str] = "instructions.library.message.status_node_generator"
STATUS_TEXT: Final[str] = "{generator} of {library_key}"
LIBRARY_FILENAME: Final[str] = "library_abc123"


def _library_key() -> InstructionLibraryKey:
    return InstructionLibraryKey(
        sample_rate=44100,
        frame_length=1470,
        window_size=2940,
        transformation_gamma=100,
        config_hash="abc123",
        filename=LIBRARY_FILENAME,
    )


def _generator_node() -> GeneratorNode:
    library = LibraryNode("Library", library_key=_library_key())
    return GeneratorNode("Pulse", generator_name=GeneratorName.PULSE, parent=library)


def _panel() -> GUIInstructionsLibraryPanel:
    panel = GUIInstructionsLibraryPanel.__new__(GUIInstructionsLibraryPanel)
    panel._language_manager = FakeLanguageManager(texts={STATUS_KEY: STATUS_TEXT})
    return panel


class TestGeneratorNodeMessage:
    def test_the_message_names_the_generator_and_its_library(self) -> None:
        """Hovering a generator row says which generator of which library it stands for."""
        panel = _panel()
        message_function = panel._create_status_bar_message_function_for_instructions_node()

        message = message_function(user_data=(_generator_node(), "row_tag"))

        assert message == f"{GeneratorName.PULSE} of {LIBRARY_FILENAME}"


class TestGeneratorNodeSelection:
    def test_a_click_names_the_library_and_the_generator(self) -> None:
        """Clicking a generator row hands on the library it belongs to and the generator it is."""
        panel = _panel()
        selected: List[Tuple[InstructionLibraryKey, GeneratorName]] = []
        panel.on_generator_selected = lambda library_key, generator_name: selected.append(
            (library_key, generator_name),
        )

        panel._on_generator_node_clicked(
            None,
            (dpg.mvMouseButton_Left, 0),
            (_generator_node(), "row_tag"),
        )

        assert selected == [(_library_key(), GeneratorName.PULSE)]

    def test_loading_from_the_row_menu_names_the_same_pair(self) -> None:
        """The row menu's load item reaches the generator the row holds, as a click does."""
        panel = _panel()
        selected: List[Tuple[InstructionLibraryKey, GeneratorName]] = []
        panel.on_generator_selected = lambda library_key, generator_name: selected.append(
            (library_key, generator_name),
        )

        panel._on_load_generator(None, True, _generator_node())

        assert selected == [(_library_key(), GeneratorName.PULSE)]
