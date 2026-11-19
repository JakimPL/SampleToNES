from sampletones_application.categories.dialog import filter_name
from sampletones_application.categories.exports import EXPORT_INSTRUMENT_FILTERS
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.utils.file_dialogs.filter import FileFilter
from sampletones_core.exports.format import ExportFormat
from sampletones_shared.paths.extensions import EXT_FILE_RECONSTRUCTION


def instrument_filter(language_manager: LanguageManager, export_format: ExportFormat, extension: str) -> FileFilter:
    """The type an instrument export in ``export_format`` writes its file as, named after the format."""
    return FileFilter.for_extensions(
        filter_name(language_manager, EXPORT_INSTRUMENT_FILTERS[export_format]), [extension]
    )


def reconstruction_filter(language_manager: LanguageManager) -> FileFilter:
    """The single type a reconstruction is written as and read from."""
    return FileFilter.for_extensions(language_manager["global.dialog.filter.reconstruction"], [EXT_FILE_RECONSTRUCTION])
