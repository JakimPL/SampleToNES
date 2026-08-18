from importlib.resources import files
from pathlib import Path

from sampletones_assets.mark.specification import Mark
from sampletones_assets.mark.vector import render_vector
from sampletones_shared.paths.resources import ICON_VECTOR_FILENAME

PLACEHOLDER_PREFIX = "$"
REPLACEMENT_COLOR = "#010203"


class TestRenderVector:
    def test_the_shipped_vector_is_what_the_definition_renders(self) -> None:
        """The committed vector is the mark's design source, so it stays in step with the definition."""
        shipped = Path(str(files("sampletones_assets.icons"))) / ICON_VECTOR_FILENAME
        assert render_vector(Mark.load()) == shipped.read_text(encoding="utf-8")

    def test_the_template_is_filled_throughout(self) -> None:
        assert PLACEHOLDER_PREFIX not in render_vector(Mark.load())

    def test_every_colour_reaches_the_document(self) -> None:
        mark = Mark.load()
        document = render_vector(mark)
        colors = (
            mark.colors.background.top,
            mark.colors.background.bottom,
            mark.colors.sine,
            mark.colors.square,
            mark.colors.rim,
        )

        for color in colors:
            assert color in document

    def test_the_document_follows_the_definition(self) -> None:
        """A colour changed in the definition is the colour the vector is drawn with."""
        mark = Mark.load()
        recolored = mark.model_copy(update={"colors": mark.colors.model_copy(update={"sine": REPLACEMENT_COLOR})})
        document = render_vector(recolored)

        assert REPLACEMENT_COLOR in document
        assert mark.colors.sine not in document

    def test_the_wave_starts_where_the_definition_places_it(self) -> None:
        mark = Mark.load()
        start = mark.waves.sine.start
        assert f'd="M{start.x:g} {start.y:g}' in render_vector(mark)
