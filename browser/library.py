import threading
from pathlib import Path
from typing import Dict, Optional

import dearpygui.dearpygui as dpg

from browser.constants import *
from constants import LIBRARY_DIRECTORY
from instructions.noise import NoiseInstruction
from instructions.pulse import PulseInstruction
from instructions.triangle import TriangleInstruction
from library.data import LibraryData
from library.key import LibraryKey
from library.library import Library
from reconstructor.maps import LIBRARY_GENERATOR_CLASS_MAP
from typehints.general import LIBRARY_GENERATOR_NAMES, GeneratorClassName


class LibraryPanel:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.library = Library(directory=LIBRARY_DIRECTORY)
        self.is_generating = False
        self.generation_thread = None

        self.library_files: Dict[str, str] = {}
        self.loaded_libraries: Dict[str, LibraryData] = {}
        self.expanded_states: Dict[str, bool] = {}
        self.current_library: Optional[str] = None

    def create_panel(self, parent_tag: str):
        with dpg.child_window(
            width=CONFIG_PANEL_WIDTH, height=LIBRARY_PANEL_HEIGHT, parent=parent_tag, tag="library_panel"
        ):
            dpg.add_text(SECTION_LIBRARY_PANEL)
            dpg.add_separator()

            dpg.add_text(MSG_LIBRARY_NOT_EXISTS, tag="library_status")

            dpg.add_separator()
            with dpg.group(tag="library_controls_group"):
                dpg.add_button(
                    label=BUTTON_GENERATE_LIBRARY, callback=self._generate_library, tag="generate_library_button"
                )
                dpg.add_button(
                    label=BUTTON_REFRESH_LIBRARIES, callback=self._on_refresh_clicked, tag="refresh_libraries_button"
                )
            dpg.add_progress_bar(tag="library_progress", default_value=0.0, show=False)

            dpg.add_separator()

            with dpg.tree_node(label="Libraries", tag="libraries_tree", default_open=True):
                pass

    def update_status(self):
        config = self.config_manager.get_config()
        key = self.config_manager.key

        if not config or not key:
            dpg.set_value("library_status", "Configuration not ready")
            dpg.configure_item("generate_library_button", enabled=False)
            return

        self.library.directory = config.general.library_directory
        if self.library.exists(key):
            library_name = self._get_display_name_from_key(key)
            dpg.set_value("library_status", f"Library {library_name} exists.")
            dpg.set_item_label("generate_library_button", BUTTON_REGENERATE_LIBRARY)
        else:
            dpg.set_value("library_status", MSG_LIBRARY_NOT_EXISTS)
            dpg.set_item_label("generate_library_button", BUTTON_GENERATE_LIBRARY)

        dpg.configure_item("generate_library_button", enabled=not self.is_generating)
        self._refresh_libraries()
        self._check_tree_expansions()
        self._sync_with_config_key(key)

    def _on_refresh_clicked(self):
        self._refresh_libraries()
        self._check_tree_expansions()

    def _generate_library(self):
        if self.is_generating:
            return

        config = self.config_manager.get_config()
        if not config:
            return

        self.is_generating = True
        dpg.configure_item("library_controls_group", enabled=False)
        dpg.set_value("library_status", MSG_GENERATING_LIBRARY)
        dpg.configure_item("library_progress", show=True)
        dpg.set_value("library_progress", 0.0)

        self.generation_thread = threading.Thread(target=self._generate_library_worker, args=(config,), daemon=True)
        self.generation_thread.start()

    def _generate_library_worker(self, config):
        try:
            window = self.config_manager.get_window()
            if not window:
                raise ValueError("Window not available")

            self.library.directory = config.general.library_directory
            self.library.update(config, window, overwrite=True)

            dpg.set_value("library_status", MSG_LIBRARY_GENERATED)
            dpg.set_value("library_progress", 1.0)
            self.update_status()
            self._refresh_libraries()
            self._check_tree_expansions()

        except Exception as exception:
            dpg.set_value("library_status", ERROR_PREFIX.format(f"generating library: {exception}"))

        finally:
            self.is_generating = False
            dpg.configure_item("library_controls_group", enabled=True)
            dpg.configure_item("library_progress", show=False)

    def _refresh_libraries(self):
        library_directory = Path(self.config_manager.config.general.library_directory)
        if not library_directory.exists():
            self._clear_libraries_tree()
            return

        new_library_files = {}
        for file_path in library_directory.iterdir():
            if file_path.is_file() and file_path.suffix == ".dat" and self._is_library_file(file_path.stem):
                display_name = self._get_display_name(file_path.stem)
                new_library_files[display_name] = file_path.stem

        if new_library_files == self.library_files:
            return

        old_library_files = self.library_files.copy()
        self.library_files = new_library_files

        current_library_still_exists = self.current_library and self.current_library in self.library_files

        children = dpg.get_item_children("libraries_tree", slot=1)
        if children:
            for child in children:
                dpg.delete_item(child)

        for display_name in sorted(self.library_files.keys()):
            with dpg.tree_node(label=display_name, tag=f"lib_{display_name}", parent="libraries_tree"):
                for generator_name in LIBRARY_GENERATOR_NAMES:
                    with dpg.tree_node(label=generator_name.capitalize(), tag=f"{generator_name}_{display_name}"):
                        dpg.add_text("Generator data will load when expanded")

        if current_library_still_exists:
            self._restore_current_library_state()

        removed_libraries = set(old_library_files.keys()) - set(self.library_files.keys())
        for removed_library in removed_libraries:
            if removed_library in self.loaded_libraries:
                del self.loaded_libraries[removed_library]

        self._check_tree_expansions()

    def _clear_libraries_tree(self):
        children = dpg.get_item_children("libraries_tree", slot=1)
        if children:
            for child in children:
                dpg.delete_item(child)
        self.library_files.clear()
        self.loaded_libraries.clear()
        self.current_library = None

    def _restore_current_library_state(self):
        if self.current_library:
            library_tag = f"lib_{self.current_library}"
            if dpg.does_item_exist(library_tag):
                dpg.configure_item(library_tag, highlight_color=(100, 150, 255, 100))

    def _is_library_file(self, file_name: str) -> bool:
        file_parts = file_name.split("_")
        if len(file_parts) < 4:
            return False
        if not file_parts[0] == "sr" or not file_parts[1].isdigit():
            return False
        if not file_parts[2] == "fl" or not file_parts[3].isdigit():
            return False
        return len(file_parts) >= 6

    def _create_key_from_file_name(self, file_name: str) -> LibraryKey:
        file_parts = file_name.split("_")
        if len(file_parts) < 8:
            raise ValueError(f"Invalid library file name format: {file_name}")

        sample_rate = int(file_parts[1])
        frame_length = int(file_parts[3])
        window_size = int(file_parts[5])
        config_hash = file_parts[7]

        return LibraryKey(
            sample_rate=sample_rate, frame_length=frame_length, window_size=window_size, config_hash=config_hash
        )

    def _get_display_name_from_key(self, key: LibraryKey) -> str:
        sample_rate = key.sample_rate
        change_rate = round(sample_rate / key.frame_length)
        hash_part = key.config_hash[:7]
        return f"{sample_rate}_{change_rate}_{hash_part}"

    def _get_display_name(self, file_name: str) -> str:
        key = self._create_key_from_file_name(file_name)
        return self._get_display_name_from_key(key)

    def _check_tree_expansions(self):
        for display_name in self.library_files.keys():
            library_tag = f"lib_{display_name}"

            if dpg.does_item_exist(library_tag):
                is_expanded = dpg.get_value(library_tag)
                was_expanded = self.expanded_states.get(display_name, False)

                if is_expanded and not was_expanded:
                    self._load_library(display_name)
                    self.expanded_states[display_name] = True
                elif not is_expanded:
                    self.expanded_states[display_name] = False

            for generator_name in LIBRARY_GENERATOR_NAMES:
                generator_tag = f"{generator_name}_{display_name}"
                if dpg.does_item_exist(generator_tag):
                    is_expanded = dpg.get_value(generator_tag)
                    generator_key = f"{display_name}_{generator_name}"
                    was_expanded = self.expanded_states.get(generator_key, False)

                    if is_expanded and not was_expanded:
                        self._load_generator_data(display_name, generator_name)
                        self.expanded_states[generator_key] = True
                    elif not is_expanded:
                        self.expanded_states[generator_key] = False

    def _load_library(self, display_name: str):
        self._set_current_library(display_name, apply_config=True)

    def _set_current_library(self, display_name: str, apply_config: bool = False):
        if display_name not in self.loaded_libraries:
            full_file_name = self.library_files[display_name]
            library_key = self._create_key_from_file_name(full_file_name)
            library_path = Path(self.config_manager.config.general.library_directory) / f"{full_file_name}.dat"

            library_data = LibraryData.load(library_path)
            self.loaded_libraries[display_name] = library_data

            if apply_config:
                self.config_manager.apply_library_config(library_key)
                print(f"Loaded library {display_name} and applied its configuration")
            else:
                print(f"Loaded library {display_name}")

        if self.current_library:
            old_tag = f"lib_{self.current_library}"
            if dpg.does_item_exist(old_tag):
                dpg.configure_item(old_tag, highlight_color=(0, 0, 0, 0))

        self.current_library = display_name
        new_tag = f"lib_{display_name}"
        if dpg.does_item_exist(new_tag):
            dpg.configure_item(new_tag, highlight_color=(100, 150, 255, 100))

    def _load_generator_data(self, display_name: str, generator_name: str):
        if display_name not in self.loaded_libraries:
            print(f"Library {display_name} not loaded yet")
            return

        print(f"Loading {generator_name} data from library {display_name}")

        generator_tag = f"{generator_name}_{display_name}"
        if dpg.does_item_exist(generator_tag):
            children = dpg.get_item_children(generator_tag, slot=1)
            if children:
                for child in children:
                    dpg.delete_item(child)

            library_data = self.loaded_libraries[display_name]
            generator_class_name = LIBRARY_GENERATOR_CLASS_MAP.get(generator_name)
            if generator_class_name:
                grouped_instructions = self._parse_instructions_by_generator(library_data, generator_class_name)
                self._display_instruction_groups(
                    display_name, generator_name, generator_class_name, grouped_instructions
                )
            else:
                dpg.add_text(f"Unknown generator: {generator_name}", parent=generator_tag)

    def _sync_with_config_key(self, config_key: LibraryKey):
        if not config_key:
            return

        matching_display_name = self._get_display_name_from_key(config_key)

        if matching_display_name in self.library_files:
            self._collapse_other_libraries(matching_display_name)
            self._expand_library_tree_node(matching_display_name)

    def _collapse_other_libraries(self, except_library: str):
        for display_name in self.library_files.keys():
            if display_name != except_library:
                library_tag = f"lib_{display_name}"
                if dpg.does_item_exist(library_tag):
                    dpg.set_value(library_tag, False)
                    self.expanded_states[display_name] = False

    def _expand_library_tree_node(self, display_name: str):
        library_tag = f"lib_{display_name}"
        if dpg.does_item_exist(library_tag):
            dpg.set_value(library_tag, True)
            self.expanded_states[display_name] = True

    def _parse_instructions_by_generator(
        self, library_data: LibraryData, generator_class_name: GeneratorClassName
    ) -> Dict[str, list]:
        generator_data = library_data.filter(generator_class_name)

        if not generator_data:
            return {}

        grouped_instructions = {}

        for instruction, fragment in generator_data.items():
            if not instruction.on:
                continue

            if isinstance(instruction, (PulseInstruction, TriangleInstruction)):
                grouping_key = f"Pitch {instruction.pitch}"
            elif isinstance(instruction, NoiseInstruction):
                grouping_key = f"Period {instruction.period}"
            else:
                grouping_key = "Other"

            if grouping_key not in grouped_instructions:
                grouped_instructions[grouping_key] = []

            grouped_instructions[grouping_key].append((instruction, fragment))

        for group_key in grouped_instructions:
            grouped_instructions[group_key].sort(key=lambda x: x[0].name)

        return grouped_instructions

    def _display_instruction_groups(
        self,
        display_name: str,
        generator_name: str,
        generator_class_name: GeneratorClassName,
        grouped_instructions: Dict[str, list],
    ):
        generator_tag = f"{generator_name}_{display_name}"

        if not grouped_instructions:
            dpg.add_text("No valid instructions found", parent=generator_tag)
            return

        for group_key, instructions in sorted(grouped_instructions.items()):
            group_tag = f"{group_key}_{generator_name}_{display_name}"
            with dpg.tree_node(label=f"{group_key} ({len(instructions)} items)", parent=generator_tag, tag=group_tag):
                for instruction, fragment in instructions:
                    dpg.add_selectable(
                        label=instruction.name,
                        callback=self._on_instruction_selected,
                        user_data=(generator_class_name, instruction),
                        parent=group_tag,
                    )

    def _on_instruction_selected(self, sender, app_data, user_data):
        generator_class_name, instruction = user_data
        self._show_instruction_details(generator_class_name, instruction)

    def _show_instruction_details(self, generator_class_name: GeneratorClassName, instruction):
        print(f"Selected {generator_class_name} instruction: {instruction.name}")
        print(f"Instruction details: {instruction.model_dump()}")
        # TODO: This will interface with the main panel to show instruction specifics
        # instead of the current configuration preview
