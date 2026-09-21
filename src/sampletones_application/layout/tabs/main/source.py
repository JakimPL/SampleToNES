from pydantic import BaseModel


class SourceSettingsLayout(BaseModel, extra="forbid", frozen=True):
    drive_decimals: int
    name_column_width: int
    choice_column_width: int
    step_button_width: int

    @property
    def drive_format(self) -> str:
        """The format a drive slider prints its value in, to the decimals a drive is set at."""
        return f"%.{self.drive_decimals}f"
