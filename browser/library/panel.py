import threading
from typing import Any, Callable, Optional, Tuple

import dearpygui.dearpygui as dpg

from browser.config.manager import ConfigManager
from browser.constants import *
from browser.library.manager import LibraryManager
from configs.config import Config
from library.key import LibraryKey
from reconstructor.maps import LIBRARY_GENERATOR_CLASS_MAP
from typehints.general import LibraryGeneratorName


class LibraryPanelGUI:
    def __init__(self, config_manager: ConfigManager, on_instruction_selected: Optional[Callable] = None) -> None:
        self.config_manager = config_manager
        self.library_manager = LibraryManager()
        self.on_instruction_selected = on_instruction_selected

        self.is_generating = False
        self.generation_thread = None
        self.current_highlighted_library: Optional[str] = None

    def create_panel(self, parent_tag: str) -> None:
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
                    label=BUTTON_REFRESH_LIBRARIES, callback=self._refresh_libraries, tag="refresh_libraries_button"
                )
            dpg.add_progress_bar(tag="library_progress", default_value=0.0, show=False)

            dpg.add_separator()

            with dpg.tree_node(label="Libraries", tag="libraries_tree", default_open=True):
                pass

    def update_status(self) -> None:
        config = self.config_manager.get_config()
        key = self.config_manager.key

        if not config or not key:
            dpg.set_value("library_status", "Configuration not ready")
            dpg.configure_item("generate_library_button", enabled=False)
            return

        self.library_manager.set_library_directory(config.general.library_directory)

        if self.library_manager.library_exists_for_key(key):
            library_name = self.library_manager._get_display_name_from_key(key)
            dpg.set_value("library_status", f"Library {library_name} exists.")
            dpg.set_item_label("generate_library_button", BUTTON_REGENERATE_LIBRARY)
        else:
            dpg.set_value("library_status", MSG_LIBRARY_NOT_EXISTS)
            dpg.set_item_label("generate_library_button", BUTTON_GENERATE_LIBRARY)

        dpg.configure_item("generate_library_button", enabled=not self.is_generating)

        self._refresh_libraries()
        self._sync_with_config_key(key)

    def _refresh_libraries(self) -> None:
        self.library_manager.gather_available_libraries()
        self._rebuild_tree()

    def _rebuild_tree(self) -> None:
        children = dpg.get_item_children("libraries_tree", slot=1)
        if children:
            for child in children:
                dpg.delete_item(child)

        libraries = self.library_manager.get_available_libraries()
        for display_name in sorted(libraries.keys()):
            self._create_library_node(display_name)

    def _create_library_node(self, display_name: str) -> None:
        library_tag = f"lib_{display_name}"
        with dpg.tree_node(label=display_name, tag=library_tag, parent="libraries_tree"):
            if self.library_manager.is_library_loaded(display_name):
                self._create_generator_nodes(display_name)

    def _create_generator_nodes(self, display_name: str) -> None:
        from typehints.general import LIBRARY_GENERATOR_NAMES

        for generator_name in LIBRARY_GENERATOR_NAMES:
            generator_tag = f"{generator_name}_{display_name}"
            with dpg.tree_node(label=generator_name.capitalize(), tag=generator_tag, parent=f"lib_{display_name}"):
                self._populate_generator_instructions(display_name, generator_name)

    def _populate_generator_instructions(self, display_name: str, generator_name: LibraryGeneratorName) -> None:
        generator_tag = f"{generator_name}_{display_name}"
        grouped_instructions = self.library_manager.get_library_instructions_by_generator(display_name, generator_name)

        if not grouped_instructions:
            dpg.add_text("No valid instructions found", parent=generator_tag)
            return

        generator_class_name = LIBRARY_GENERATOR_CLASS_MAP.get(generator_name)
        for group_key, instructions in sorted(grouped_instructions.items()):
            group_tag = f"{group_key}_{generator_name}_{display_name}"
            with dpg.tree_node(label=f"{group_key} ({len(instructions)} items)", parent=generator_tag, tag=group_tag):
                for instruction, fragment in instructions:
                    dpg.add_selectable(
                        label=instruction.name,
                        callback=self._on_instruction_selected_internal,
                        user_data=(generator_class_name, instruction),
                        parent=group_tag,
                    )

    def _sync_with_config_key(self, config_key: LibraryKey) -> None:
        matching_display_name = self.library_manager.sync_with_config_key(config_key)
        if matching_display_name:
            self._set_current_library(matching_display_name, load_if_needed=True, apply_config=False)

    def _set_current_library(self, display_name: str, load_if_needed: bool = True, apply_config: bool = False) -> None:
        if load_if_needed and not self.library_manager.is_library_loaded(display_name):
            if self.library_manager.load_library(display_name):
                self._refresh_single_library_display(display_name)

        if apply_config:
            library_key = self.library_manager.get_library_key_for_config_update(display_name)
            if library_key:
                self.config_manager.apply_library_config(library_key)

        self._update_library_highlighting(display_name)

    def _refresh_single_library_display(self, display_name: str) -> None:
        library_tag = f"lib_{display_name}"
        if dpg.does_item_exist(library_tag):
            children = dpg.get_item_children(library_tag, slot=1)
            if children:
                for child in children:
                    dpg.delete_item(child)
            self._create_generator_nodes(display_name)

    def _update_library_highlighting(self, new_library: str) -> None:
        # TODO: Implement proper highlighting when DearPyGui supports it
        # For now, just track the current library without visual highlighting
        self.current_highlighted_library = new_library

    def _generate_library(self) -> None:
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

    def _generate_library_worker(self, config: Config) -> None:
        try:
            window = self.config_manager.get_window()
            if not window:
                raise ValueError("Window not available")

            self.library_manager.generate_library(config, window, overwrite=True)

            dpg.set_value("library_status", MSG_LIBRARY_GENERATED)
            dpg.set_value("library_progress", 1.0)
            self.update_status()

        except Exception as exception:  # TODO: to narrow
            dpg.set_value("library_status", ERROR_PREFIX.format(f"generating library: {exception}"))

        finally:
            self.is_generating = False
            dpg.configure_item("library_controls_group", enabled=True)
            dpg.configure_item("library_progress", show=False)

    def _on_instruction_selected_internal(self, sender: Any, app_data: Any, user_data: Tuple[Any, Any]) -> None:
        if self.on_instruction_selected:
            generator_class_name, instruction = user_data
            self.on_instruction_selected(generator_class_name, instruction)
