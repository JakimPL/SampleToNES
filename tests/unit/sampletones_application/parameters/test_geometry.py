from sampletones_application.layout.config import LayoutConfig
from sampletones_application.parameters.geometry import TabGeometry


class TestTabGeometryFromConfig:
    """The shared geometry core reads its six scalars from the storage paths the coordinators
    used to reach through, so the deep-path knowledge lives in one factory instead of four."""

    def test_flattens_the_geometry_paths(self, layout_config: LayoutConfig) -> None:
        geometry = TabGeometry.from_config(layout_config)

        assert geometry.side_width == layout_config.general.columns.side.width
        assert geometry.side_height == layout_config.general.columns.side.height
        assert geometry.center_weight == layout_config.general.columns.center_weight
        assert geometry.baseline_viewport_width == layout_config.general.responsive.baseline_viewport_width
        assert geometry.rail_width == layout_config.general.collapse.rail_width
        assert geometry.panel_gap == layout_config.general.panel_gap
