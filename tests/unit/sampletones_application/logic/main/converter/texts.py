from typing import Dict, Final

from sampletones_application.logic.main.converter.messages import ConverterMessages
from tests.suite.language import FakeLanguageManager

TEXTS: Final[Dict[str, str]] = {
    "main.converter.label.convert_sample_button": "Convert sample",
    "main.converter.label.convert_directory_button": "Convert directory",
    "main.converter.label.convert_stems_button": "Convert stems",
    "main.converter.label.cancel_button": "Cancel",
    "main.converter.template.convert_label_template": "{}: {}",
    "main.converter.template.progress_template": "Progress: {}/{} files",
    "main.converter.template.single_progress_template": "Reconstructing {}...",
    "main.converter.template.stage_template": " - {stage} {completed}/{total}",
    "main.converter.message.stage_loading": "reading",
    "main.converter.message.stage_matching": "matching",
    "main.converter.message.stage_decoding": "decoding",
    "main.converter.message.stage_rendering": "rendering",
    "global.dialog.template.time_estimation": "",
}


def messages() -> ConverterMessages:
    """The converter's phrases over a language manager stating the ones a test reads."""
    return ConverterMessages(FakeLanguageManager(TEXTS))  # type: ignore[arg-type]
