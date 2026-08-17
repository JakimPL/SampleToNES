from typing import Final

from tests.suite.browser import BrowserCorpus, as_view, view

WHOLE_TREE: Final[str] = as_view("""
    > By configuration
      > 8 kHz·60 Hz·CQT·γ2·P
        - sweep
      > 44.1 kHz·30 Hz
        > CQT·γ0·PTN
          - beat
          - solo
        > FFT·γ0
          > PT
            > takes
              - alt
            - beat
          > PTN·#aaaaaaa
            > drums
              - kick
              - snare
            - beat
            - melody
          > PTN·#bbbbbbb
            > drums
              - kick
            - beat
            - melody
      > archive
        > 48 kHz·50 Hz·LogFFT·γ1·TN
          - song
      - stray
    > By sample
      > beat
        - 44.1 kHz·30 Hz·CQT·γ0·PTN
        - 44.1 kHz·30 Hz·FFT·γ0·PT
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#aaaaaaa
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb
      > drums
        > kick
          - 44.1 kHz·30 Hz·FFT·γ0·PTN·#aaaaaaa
          - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb
        - snare·44.1 kHz·30 Hz·FFT·γ0·PTN
      > melody
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#aaaaaaa
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb
      - solo·44.1 kHz·30 Hz·CQT·γ0·PTN
      - sweep·8 kHz·60 Hz·CQT·γ2·P
      - takes·alt·44.1 kHz·30 Hz·FFT·γ0·PT
    """)


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
