import threading
from pathlib import Path
from typing import Optional

import dearpygui.dearpygui as dpg

from browser.constants import *
from ffts.window import Window
from library.library import Library


class LibraryPanel:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.library = Library(directory="")
        self.is_generating = False
        self.generation_thread: Optional[threading.Thread] = None

    def create_panel(self, parent_tag: str):
        with dpg.child_window(width=CONFIG_PANEL_WIDTH, height=LIBRARY_PANEL_HEIGHT, parent=parent_tag):
            dpg.add_text(SECTION_LIBRARY_PANEL)
            dpg.add_separator()

            dpg.add_text(MSG_LIBRARY_NOT_EXISTS, tag="library_status")

            dpg.add_separator()
            dpg.add_button(
                label=BUTTON_GENERATE_LIBRARY, callback=self._generate_library, tag="generate_library_button"
            )
            dpg.add_progress_bar(tag="library_progress", default_value=0.0, show=False)

    def update_status(self):
        config = self.config_manager.get_config()
        key = self.config_manager.key

        if not config or not key:
            dpg.set_value("library_status", "Configuration not ready")
            dpg.configure_item("generate_library_button", enabled=False)
            return

        try:
            self.library.directory = config.general.library_directory
            if self.library.exists(key):
                dpg.set_value("library_status", MSG_LIBRARY_EXISTS)
                dpg.set_value("generate_library_button", "Regenerate library")
            else:
                dpg.set_value("library_status", MSG_LIBRARY_NOT_EXISTS)
                dpg.set_value("generate_library_button", BUTTON_GENERATE_LIBRARY)

            dpg.configure_item("generate_library_button", enabled=not self.is_generating)

        except Exception as exception:
            dpg.set_value("library_status", ERROR_PREFIX.format(f"checking library: {exception}"))
            dpg.configure_item("generate_library_button", enabled=False)

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
                raise Exception("Window not available")

            self.library.directory = config.general.library_directory
            self.library.update(config, window, overwrite=True)

            dpg.set_value("library_status", MSG_LIBRARY_GENERATED)
            dpg.set_value("library_progress", 1.0)
            self.update_status()

        except Exception as exception:
            dpg.set_value("library_status", ERROR_PREFIX.format(f"generating library: {exception}"))

        finally:
            self.is_generating = False
            dpg.configure_item("generate_library_button", enabled=True)
            dpg.configure_item("library_progress", show=False)
