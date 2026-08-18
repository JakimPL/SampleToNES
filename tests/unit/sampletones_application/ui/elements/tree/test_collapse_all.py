from typing import List, Tuple

import pytest

from sampletones_application.ui.elements.tree import tree as tree_module
from sampletones_core.structures.tree import NodeType
from tests.suite.browser import (
    WHOLE_TREE,
    BrowserCorpus,
    build_browser_panel,
    render_view,
    row_named,
    set_row_expanded,
)


@pytest.fixture
def folded(monkeypatch: pytest.MonkeyPatch) -> List[Tuple[str, bool]]:
    """Records the tag and open state of every row the control reaches."""
    calls: List[Tuple[str, bool]] = []
    monkeypatch.setattr(
        tree_module,
        "dpg_set_value",
        lambda tag, value: calls.append((tag, value)),
    )
    return calls


class TestCollapseAllControl:
    """The control folds the whole tree away, and the browser is left holding that shape."""

    def test_every_row_holding_something_is_folded(
        self,
        corpus: BrowserCorpus,
        folded: List[Tuple[str, bool]],
    ) -> None:
        panel = build_browser_panel(corpus, set(), favorites_only=False)

        panel._on_collapse_all_clicked()

        containers = {panel._generate_node_tag(node) for node in corpus.tree.get_root().descendants if node.children}
        assert {tag for tag, _ in folded} == containers
        assert all(not expanded for _, expanded in folded)

    def test_a_row_holding_nothing_is_left_alone(
        self,
        corpus: BrowserCorpus,
        folded: List[Tuple[str, bool]],
    ) -> None:
        panel = build_browser_panel(corpus, set(), favorites_only=False)

        panel._on_collapse_all_clicked()

        leaves = {
            panel._generate_node_tag(node)
            for node in corpus.tree.get_root().descendants
            if node.node_type == NodeType.FILE
        }
        assert not leaves & {tag for tag, _ in folded}

    def test_the_shape_the_control_left_is_what_the_next_pass_draws(
        self,
        corpus: BrowserCorpus,
        folded: List[Tuple[str, bool]],
    ) -> None:
        panel = build_browser_panel(corpus, set(), favorites_only=False)
        set_row_expanded(panel, row_named(corpus, "archive"), expanded=True)
        set_row_expanded(panel, row_named(corpus, "takes"), expanded=True)
        render_view(panel)

        panel._on_collapse_all_clicked()

        assert panel._expanded_rows == set()
        assert render_view(panel) == WHOLE_TREE
