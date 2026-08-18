from pydantic import BaseModel, Field


class BrowserConfig(BaseModel):
    auto_expand_favorite_reconstructions: bool = Field(
        default=False,
        description="If showing the favorites alone opens the rows above a favorite reconstruction.",
    )
    auto_expand_favorite_directories: bool = Field(
        default=False,
        description="If showing the favorites alone opens the rows above a favorite directory.",
    )
