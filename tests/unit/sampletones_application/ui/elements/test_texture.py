from typing import Iterator

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.tags.general import TAG_GLOBAL_TEXTURE_LOGO
from sampletones_application.ui.elements.texture import TextureRegistry

MARK_SIZE = 256


@pytest.fixture
def context() -> Iterator[None]:
    """A DearPyGui context, textures being framework items rather than plain data."""
    dpg.create_context()
    try:
        yield
    finally:
        dpg.destroy_context()


class TestTheImagesTheInterfaceDraws:
    def test_the_mark_is_read_into_a_texture_named_by_its_tag(self, context: None) -> None:
        TextureRegistry.register_textures()

        assert dpg.does_item_exist(TAG_GLOBAL_TEXTURE_LOGO)

    def test_the_texture_carries_the_shipped_image_at_its_own_size(self, context: None) -> None:
        """The image is read as it ships, and whatever draws it states the size it wants."""
        TextureRegistry.register_textures()

        configuration = dpg.get_item_configuration(TAG_GLOBAL_TEXTURE_LOGO)
        assert (configuration["width"], configuration["height"]) == (MARK_SIZE, MARK_SIZE)

    def test_the_texture_is_there_to_be_drawn(self, context: None) -> None:
        TextureRegistry.register_textures()

        with dpg.window():
            image = dpg.add_image(TAG_GLOBAL_TEXTURE_LOGO, width=72, height=72)

        assert dpg.get_item_type(image) == "mvAppItemType::mvImage"
