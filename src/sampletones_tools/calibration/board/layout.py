from typing import Final, Tuple

PAGE_FILE: Final[str] = "index.html"
STYLE_FILE: Final[str] = "style.css"
SCRIPT_FILE: Final[str] = "page.js"
PALETTE_FILE: Final[str] = "palette.css"
FONTS_FILE: Final[str] = "fonts.css"
DATA_FILE: Final[str] = "data.js"

PAGE_DIRECTORY: Final[str] = "page"
AUDIO_DIRECTORY: Final[str] = "audio"

SHIPPED_FILES: Final[Tuple[str, ...]] = (PAGE_FILE, STYLE_FILE, SCRIPT_FILE)
GENERATED_FILES: Final[Tuple[str, ...]] = (PALETTE_FILE, FONTS_FILE, DATA_FILE)
