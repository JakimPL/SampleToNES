from tests.suite.browser import WHOLE_TREE, BrowserCorpus, view


class TestWholeTree:
    """What a reconstructions directory reads as with nothing to narrow it, in both views.

    The corpus states what the browser has to tell apart, and this is the shape it gives it: two
    configurations differing by hash alone marked with that hash, a frequency holding two methods
    beside one whose whole chain folded into a single row, an audio gathering the configurations
    that reconstructed it, a sample of one variant folded into that variant, a configuration
    directory nested in a plain folder, and a reconstruction outside every configuration directory.
    """

    def test_the_whole_tree_is_drawn_with_every_row_folded(self, corpus: BrowserCorpus) -> None:
        assert view(corpus, set(), favorites_only=False) == WHOLE_TREE
