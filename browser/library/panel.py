import threading
from typing import Any, Callable, Optional, Tuple

import dearpygui.dearpygui as dpg

from browser.config.manager import ConfigManager
from browser.constants import *
from browser.library.manager import LibraryManager
from configs.config import Config
from library.data import LibraryFragment
from library.key import LibraryKey
from reconstructor.maps import LIBRARY_GENERATOR_CLASS_MAP
from typehints.general import LibraryGeneratorName
from typehints.instructions import InstructionUnion


class LibraryPanelGUI:
    def __init__(
        self,
        config_manager: ConfigManager,
        on_instruction_selected: Optional[Callable] = None,
        on_config_gui_update: Optional[Callable] = None,
    ) -> None:
        self.config_manager = config_manager
        self.library_manager = LibraryManager()
        self.on_instruction_selected = on_instruction_selected
        self.on_config_gui_update = on_config_gui_update

        self.is_generating = False
        self.generation_thread = None
        self.current_highlighted_library: Optional[str] = None

    def create_panel(self):
        with dpg.group(tag=TAG_LIBRARY_PANEL) as library_panel_group:
            dpg.add_text(LBL_LIBRARY_LIBRARIES)
            dpg.add_separator()
            dpg.add_text(MSG_LIBRARY_NOT_LOADED, tag=TAG_LIBRARY_STATUS)

            with dpg.group(tag=TAG_LIBRARY_CONTROLS_GROUP) as controls_group:
                dpg.add_button(
                    label=LBL_BUTTON_GENERATE_LIBRARY, callback=self._generate_library, tag=TAG_LIBRARY_BUTTON_GENERATE
                )
                dpg.add_button(label=LBL_BUTTON_REFRESH_LIBRARIES, callback=self._refresh_libraries)
                dpg.add_progress_bar(tag=TAG_LIBRARY_PROGRESS, show=False)

            dpg.add_separator()
            with dpg.tree_node(label=LBL_LIBRARY_AVAILABLE_LIBRARIES, tag=TAG_LIBRARY_TREE, default_open=True):
                pass

        return library_panel_group

    def initialize_libraries(self) -> None:
        self._refresh_libraries()
        key = self.config_manager.key
        if key is not None:
            self._sync_with_config_key(key)

    def update_status(self) -> None:
        config = self.config_manager.get_config()
        key = self.config_manager.key

        if not config or not key:
            dpg.set_value(TAG_LIBRARY_STATUS, MSG_CONFIG_NOT_READY)
            dpg.configure_item(TAG_LIBRARY_BUTTON_GENERATE, enabled=False)
            return

        library_name = self.library_manager._get_display_name_from_key(key)
        if self.library_manager.library_exists_for_key(key):
            dpg.set_value(TAG_LIBRARY_STATUS, TPL_LIBRARY_EXISTS.format(library_name))
            dpg.set_item_label(TAG_LIBRARY_BUTTON_GENERATE, LBL_BUTTON_REGENERATE_LIBRARY)
        else:
            dpg.set_value(TAG_LIBRARY_STATUS, TPL_LIBRARY_NOT_EXISTS.format(library_name))
            dpg.set_item_label(TAG_LIBRARY_BUTTON_GENERATE, LBL_BUTTON_GENERATE_LIBRARY)

        dpg.configure_item(TAG_LIBRARY_BUTTON_GENERATE, enabled=not self.is_generating)

    def _refresh_libraries(self) -> None:
        self.library_manager.gather_available_libraries()
        self._rebuild_tree()
        key = self.config_manager.key
        if key is not None:
            self._sync_with_config_key(key)

    def _rebuild_tree(self) -> None:
        self._clear_children(TAG_LIBRARY_TREE)

        libraries = self.library_manager.get_available_libraries()
        for display_name in sorted(libraries.keys()):
            self._create_library_node(display_name)

    def _create_library_node(self, display_name: str) -> None:
        library_tag = TPL_LIBRARY_TAG.format(display_name)
        is_current = self._is_current_library(display_name)

        if is_current and not self.library_manager.is_library_loaded(display_name):
            self.library_manager.load_library(display_name)

        with dpg.tree_node(label=display_name, tag=library_tag, parent=TAG_LIBRARY_TREE, default_open=is_current):
            if self.library_manager.is_library_loaded(display_name):
                self._create_generator_nodes(display_name)
            else:
                dpg.add_selectable(
                    label=MSG_LIBRARY_NOT_LOADED,
                    callback=self._on_load_library_clicked,
                    user_data=display_name,
                    parent=library_tag,
                )

    def _create_generator_nodes(self, display_name: str) -> None:
        from typehints.general import LIBRARY_GENERATOR_NAMES

        for generator_name in LIBRARY_GENERATOR_NAMES:
            generator_tag = TPL_GENERATOR_TAG.format(generator_name, display_name)
            with dpg.tree_node(
                label=generator_name.capitalize(), tag=generator_tag, parent=TPL_LIBRARY_TAG.format(display_name)
            ):
                self._populate_generator_instructions(display_name, generator_name)

    def _populate_generator_instructions(self, display_name: str, generator_name: LibraryGeneratorName) -> None:
        generator_tag = TPL_GENERATOR_TAG.format(generator_name, display_name)
        grouped_instructions = self.library_manager.get_library_instructions_by_generator(display_name, generator_name)

        if not grouped_instructions:
            dpg.add_text(MSG_LIBRARY_NO_VALID_INSTRUCTIONS, parent=generator_tag)
            return

        generator_class_name = LIBRARY_GENERATOR_CLASS_MAP.get(generator_name)
        for group_key, instructions in grouped_instructions.items():
            group_tag = TPL_GROUP_TAG.format(group_key, generator_name, display_name)
            with dpg.tree_node(
                label=TPL_GROUP_LABEL.format(group_key, len(instructions)), parent=generator_tag, tag=group_tag
            ):
                for instruction, _ in instructions:
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
            if library_key and self.on_config_gui_update:
                self.on_config_gui_update(library_key)

        self._update_library_highlighting(display_name)

    def _refresh_single_library_display(self, display_name: str) -> None:
        library_tag = TPL_LIBRARY_TAG.format(display_name)
        if dpg.does_item_exist(library_tag):
            self._clear_children(library_tag)
            self._create_generator_nodes(display_name)

    def _clear_children(self, parent_tag: str) -> None:
        children = dpg.get_item_children(parent_tag, slot=VAL_GLOBAL_DEFAULT_SLOT) or []
        for child in children:
            dpg.delete_item(child)

    def _update_library_highlighting(self, new_library: str) -> None:
        # TODO: Implement item highlighting properly
        self.current_highlighted_library = new_library

    def _generate_library(self) -> None:
        if self.is_generating:
            return

        config = self.config_manager.get_config()
        if not config:
            return

        self.is_generating = True
        dpg.configure_item(TAG_LIBRARY_CONTROLS_GROUP, enabled=False)
        dpg.set_value(TAG_LIBRARY_STATUS, MSG_LIBRARY_GENERATING)
        dpg.configure_item(TAG_LIBRARY_PROGRESS, show=True)
        dpg.set_value(TAG_LIBRARY_PROGRESS, VAL_GLOBAL_DEFAULT_FLOAT)

        self.generation_thread = threading.Thread(target=self._generate_library_worker, args=(config,), daemon=True)
        self.generation_thread.start()

    def _generate_library_worker(self, config: Config) -> None:
        try:
            window = self.config_manager.get_window()
            if not window:
                raise ValueError(MSG_GLOBAL_WINDOW_NOT_AVAILABLE)

            self.library_manager.generate_library(config, window, overwrite=True)

            dpg.set_value(TAG_LIBRARY_STATUS, MSG_LIBRARY_GENERATED_SUCCESSFULLY)
            dpg.set_value(TAG_LIBRARY_PROGRESS, VAL_GLOBAL_PROGRESS_COMPLETE)
            self.update_status()

        except Exception as exception:  # TODO: to narrow
            dpg.set_value(TAG_LIBRARY_STATUS, PFX_GLOBAL_ERROR.format(f"{MSG_LIBRARY_ERROR_GENERATING}: {exception}"))

        finally:
            self.is_generating = False
            dpg.configure_item(TAG_LIBRARY_CONTROLS_GROUP, enabled=True)
            dpg.configure_item(TAG_LIBRARY_PROGRESS, show=False)

    def _is_current_library(self, display_name: str) -> bool:
        if not self.config_manager.key:
            return False
        expected_display_name = self.library_manager._get_display_name_from_key(self.config_manager.key)
        return display_name == expected_display_name

    def _on_load_library_clicked(self, sender: Any, app_data: Any, user_data: str) -> None:
        display_name = user_data
        dpg.set_item_label(sender, MSG_LIBRARY_LOADING)
        if self.library_manager.load_library(display_name):
            self._refresh_single_library_display(display_name)
            self._set_current_library(display_name, load_if_needed=False, apply_config=True)

    def _on_instruction_selected_internal(self, sender: Any, app_data: Any, user_data: Tuple[Any, Any]) -> None:
        generator_class_name, instruction = user_data
        library_config = self.config_manager.get_config()
        if self.on_instruction_selected and library_config is not None:
            library_config = library_config.library
            fragment = self._get_fragment_for_instruction(instruction)
            self.on_instruction_selected(generator_class_name, instruction, fragment, library_config=library_config)

    def _get_fragment_for_instruction(self, instruction: InstructionUnion) -> Optional[LibraryFragment]:
        for display_name in self.library_manager.get_available_libraries().keys():
            if self.library_manager.is_library_loaded(display_name):
                library_data = self.library_manager.get_library_data(display_name)
                if library_data and instruction in library_data.data:
                    return library_data.data[instruction]

        return None
