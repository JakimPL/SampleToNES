import threading
from pathlib import Path
from typing import Dict, Optional, Set

import dearpygui.dearpygui as dpg

from browser.constants import *
from configs.config import Config
from ffts.window import Window
from library.data import LibraryData
from library.key import LibraryKey
from library.library import Library
from typehints.general import LIBRARY_GENERATOR_NAMES


class LibraryPanel:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.library = Library(directory="")
        self.is_generating = False
        self.generation_thread = None

        self.library_files: Dict[str, str] = {}
        self.loaded_libraries: Dict[str, LibraryData] = {}

    def create_panel(self, parent_tag: str):
        with dpg.child_window(width=CONFIG_PANEL_WIDTH, height=LIBRARY_PANEL_HEIGHT, parent=parent_tag):
            dpg.add_text(SECTION_LIBRARY_PANEL)
            dpg.add_separator()

            dpg.add_text(MSG_LIBRARY_NOT_EXISTS, tag="library_status")

            dpg.add_separator()
            dpg.add_button(
                label=BUTTON_GENERATE_LIBRARY, callback=self._generate_library, tag="generate_library_button"
            )
            dpg.add_button(
                label=BUTTON_REFRESH_LIBRARIES, callback=self._refresh_libraries, tag="refresh_libraries_button"
            )
            dpg.add_progress_bar(tag="library_progress", default_value=0.0, show=False)

            dpg.add_separator()
            dpg.add_text("Available libraries:")

            with dpg.tree_node(label="Libraries", tag="libraries_tree", default_open=True):
                dpg.add_text("Scan directory to see available libraries", tag="no_libraries_text")

    def update_status(self):
        config = self.config_manager.get_config()
        key = self.config_manager.key

        if not config or not key:
            dpg.set_value("library_status", "Configuration not ready")
            dpg.configure_item("generate_library_button", enabled=False)
            return

        self.library.directory = config.general.library_directory
        if self.library.exists(key):
            dpg.set_value("library_status", MSG_LIBRARY_EXISTS)
            dpg.set_value("generate_library_button", BUTTON_REGENERATE_LIBRARY)
        else:
            dpg.set_value("library_status", MSG_LIBRARY_NOT_EXISTS)
            dpg.set_value("generate_library_button", BUTTON_GENERATE_LIBRARY)

        dpg.configure_item("generate_library_button", enabled=not self.is_generating)
        self._refresh_libraries()

    def _generate_library(self):
        if self.is_generating:
            return

        config = self.config_manager.get_config()
        if not config:
            return

        self.is_generating = True
        dpg.configure_item("generate_library_button", enabled=False)
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

        except Exception as exception:
            dpg.set_value("library_status", ERROR_PREFIX.format(f"generating library: {exception}"))

        finally:
            self.is_generating = False
            dpg.configure_item("generate_library_button", enabled=True)
            dpg.configure_item("library_progress", show=False)

    def _refresh_libraries(self):
        if dpg.does_item_exist("library_tree"):
            dpg.delete_item("library_tree")

        self.library_files.clear()
        self.loaded_libraries.clear()

        library_directory = Path(self.config_manager.config.general.library_directory)
        if not library_directory.exists():
            return

        for directory_path in library_directory.iterdir():
            if directory_path.is_dir() and self._is_library_directory(directory_path.name):
                display_name = self._get_display_name(directory_path.name)
                self.library_files[display_name] = directory_path.name

        if self.library_files:
            with dpg.tree_node(label="Available libraries", tag="library_tree", parent="library_panel"):
                for display_name in sorted(self.library_files.keys()):
                    with dpg.tree_node(label=display_name, tag=f"lib_{display_name}"):
                        for generator_name in LIBRARY_GENERATOR_NAMES:
                            dpg.add_tree_node(
                                label=generator_name.capitalize(),
                                callback=self._on_library_selected,
                                user_data=(display_name, generator_name),
                                tag=f"{generator_name}_{display_name}",
                            )

    def _is_library_directory(self, directory_name: str) -> bool:
        directory_parts = directory_name.split("_")
        if len(directory_parts) < 4:
            return False
        if not directory_parts[0] == "sr" or not directory_parts[1].isdigit():
            return False
        if not directory_parts[2] == "fl" or not directory_parts[3].isdigit():
            return False
        return len(directory_parts) >= 6

    def _get_display_name(self, directory_name: str) -> str:
        directory_parts = directory_name.split("_")
        if len(directory_parts) >= 6:
            sample_rate = directory_parts[1]
            fragment_length = directory_parts[3]
            hash_part = directory_parts[-1][:7] if directory_parts[-1] else "unknown"
            return f"{sample_rate}_{fragment_length}_{hash_part}"
        return directory_name

    def _on_library_selected(self, sender, app_data, user_data):
        display_name, generator_type = user_data
        full_directory_name = self.library_files.get(display_name)

        if not full_directory_name:
            return

        if display_name not in self.loaded_libraries:
            library_key = self._create_key_from_directory_name(full_directory_name)
            if library_key:
                library_path = (
                    Path(self.config_manager.config.general.library_directory)
                    / full_directory_name
                    / f"{library_key.filename}"
                )
                if library_path.exists():
                    library_data = LibraryData.load(library_path)
                    self.loaded_libraries[display_name] = library_data

                    self._apply_config_from_key(library_key)

        print(f"Selected {generator_type} from library {display_name}")

    def _create_key_from_directory_name(self, directory_name: str) -> Optional[LibraryKey]:
        directory_parts = directory_name.split("_")
        if len(directory_parts) >= 8:
            sample_rate = int(directory_parts[1])
            frame_length = int(directory_parts[3])
            window_size = int(directory_parts[5])
            config_hash = directory_parts[7]

            return LibraryKey(
                sample_rate=sample_rate, frame_length=frame_length, window_size=window_size, config_hash=config_hash
            )
        return None

    def _apply_config_from_key(self, library_key: LibraryKey):
        old_config = self.config_manager.config
        new_library_config = old_config.library.model_copy(update={"sample_rate": library_key.sample_rate})
        new_config = old_config.model_copy(update={"library": new_library_config})
        self.config_manager.config = new_config
        self.config_manager._update_config()
