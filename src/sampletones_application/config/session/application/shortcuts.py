from typing import Dict

from pydantic import BaseModel, Field

from sampletones_application.constants.keybindings import DEFAULT_SCHEME_NAME


class ShortcutsConfig(BaseModel):
    """The keys the application answers to: the scheme it runs under and the actions rebound on it.

    A scheme names a whole set of keys the build ships, while an override rebinds one action on top
    of it, so a reader who changes a single combination keeps every other key the scheme gives them.
    Both are stored by name — the same names a keybinding file writes — which lets a preference
    outlive the build that wrote it, since the names a build carries are what it reads back.
    """

    scheme: str = Field(
        default=DEFAULT_SCHEME_NAME,
        description="The name of the keybinding scheme the application resolves its keys against.",
    )
    overrides: Dict[str, str] = Field(
        default_factory=dict,
        description="The combination each rebound action answers to, keyed by the action's name.",
    )
