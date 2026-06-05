from typing import Final

# Project archive layout
PROJECT_DOCUMENT_NAME: Final[str] = "project.json"
RECONSTRUCTIONS_DIRECTORY: Final[str] = "reconstructions"

# Project info defaults
DEFAULT_PROJECT_TITLE: Final[str] = ""
DEFAULT_PROJECT_AUTHOR: Final[str] = ""
DEFAULT_PROJECT_COMMENT: Final[str] = ""

# Project info length limits
MAX_PROJECT_TITLE_LENGTH: Final[int] = 64
MAX_PROJECT_AUTHOR_LENGTH: Final[int] = 64
MAX_PROJECT_COMMENT_LENGTH: Final[int] = 65536

# Song timing
DEFAULT_TEMPO: Final[int] = 150
MIN_TEMPO: Final[int] = 1
MAX_TEMPO: Final[int] = 300

DEFAULT_SPEED: Final[int] = 6
MIN_SPEED: Final[int] = 1
MAX_SPEED: Final[int] = 31

# Patterns
DEFAULT_ROWS_PER_PATTERN: Final[int] = 64
MIN_ROWS_PER_PATTERN: Final[int] = 1
MAX_ROWS_PER_PATTERN: Final[int] = 256
