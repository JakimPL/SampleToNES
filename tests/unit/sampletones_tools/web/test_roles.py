import pytest

from sampletones_tools.web.design import ApplicationDesign, palette_names
from sampletones_tools.web.roles.resolver import resolve_roles
from sampletones_tools.web.roles.table import CHANNEL_ROLE_PREFIX, COLOR_ROLES, DIMENSION_ROLES, channel_role


class TestRoleTable:
    @pytest.mark.parametrize("name", palette_names())
    def test_every_role_resolves_in_every_palette(self, name: str) -> None:
        sheet = resolve_roles(ApplicationDesign.load(name))

        assert set(sheet.colors) == set(COLOR_ROLES)
        assert set(sheet.dimensions) == set(DIMENSION_ROLES)

    def test_a_role_reads_what_the_bound_theme_states(self, design: ApplicationDesign) -> None:
        sheet = resolve_roles(design)

        assert sheet.colors["recess"] == COLOR_ROLES["recess"].resolve(design)
        assert sheet.colors["heading"] != sheet.colors["text"]

    def test_a_dimension_reads_the_layout(self, design: ApplicationDesign) -> None:
        assert resolve_roles(design).dimensions["header-height"] == design.general.collapse.header_bar_height


class TestChannelRole:
    def test_a_channel_stands_under_the_prefix(self) -> None:
        assert channel_role("noise") == f"{CHANNEL_ROLE_PREFIX}noise"

    def test_every_channel_role_is_in_the_table(self) -> None:
        for channel in ("pulse1", "pulse2", "triangle", "noise"):
            assert channel_role(channel) in COLOR_ROLES
