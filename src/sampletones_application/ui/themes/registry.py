from typing import ClassVar, Dict, Optional

from sampletones_application.ui.themes.theme import Theme


class ThemeRegistry:
    _registry: ClassVar[Dict[str, Theme]] = {}

    @classmethod
    def register(cls, theme: Theme) -> None:
        cls._registry[theme.tag] = theme

    @classmethod
    def get(cls, tag: str) -> Theme:
        if tag not in cls._registry:
            raise KeyError(f"Theme {tag!r} is not registered. Did you call setup_themes()?")

        return cls._registry[tag]

    @classmethod
    def resolve(cls, theme: Optional[Theme], default_tag: str) -> Theme:
        return theme if theme is not None else cls.get(default_tag)

    @classmethod
    def clear(cls) -> None:
        cls._registry.clear()
