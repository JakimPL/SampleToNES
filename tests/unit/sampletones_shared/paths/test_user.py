from sampletones_shared.paths.user import (
    LIBRARY_DIRECTORY,
    PROJECTS_DIRECTORY,
    RECONSTRUCTIONS_DIRECTORY,
)


class TestUserDirectories:
    def test_the_user_directories_exist_after_import(self) -> None:
        """Importing the module creates the directories the application saves into."""
        for directory in (
            LIBRARY_DIRECTORY,
            PROJECTS_DIRECTORY,
            RECONSTRUCTIONS_DIRECTORY,
        ):
            assert directory.is_dir()
