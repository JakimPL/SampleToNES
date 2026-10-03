from typing import List

from sampletones_core.compatibility.kind import ObjectKind
from tests.screens.application.old_files.constants import NAME_FIELD, SAMPLES_FIELD
from tests.suite.compatibility import ARCHIVED_VERSIONS, archived, stored_document
from tests.suite.screens.screen import Screen
from tests.suite.screens.seeds.archives import Damage
from tests.suite.screens.views.notices import Notice
from tests.suite.screens.worlds.home import HomeFile, World, screen_filling_state


def future_version(current: str) -> str:
    """A data version one major step past ``current``."""
    major, _ = current.split(".", 1)
    return f"{int(major) + 1}.0"


def stored_voice_names() -> List[str]:
    """The voice names the archived project stores, read off its document without the application's model."""
    document = stored_document(archived(ObjectKind.PROJECT, ARCHIVED_VERSIONS[ObjectKind.PROJECT]))
    return [sample[NAME_FIELD] for sample in document[SAMPLES_FIELD]]


def damaged_name(damage: Damage, suffix: str) -> str:
    """The file name a document with ``damage`` takes, ending in ``suffix``."""
    return f"{damage.name.lower()}{suffix}"


def stated_version(damage: Damage, current: str, older: str) -> str:
    """The version the application states when refusing a file with ``damage``: ``older`` or a future one."""
    return older if damage is Damage.OLDER_VERSION else future_version(current)


def world_of(*files: HomeFile) -> World:
    """A home with a screen-filling session and ``files``."""
    return World(
        state=screen_filling_state(),
        application_config=None,
        config=None,
        files=files,
    )


def shown_notice(screen: Screen) -> Notice:
    """Waits for an error or a file-not-found notice and returns the one shown."""
    notices = (screen.error_notice, screen.file_not_found_notice)
    screen.expect(lambda: any(notice.is_shown() for notice in notices), bool, description="a notice")
    return next(notice for notice in notices if notice.is_shown())
