from sampletones_tools.corpus.catalog import CatalogSpec
from sampletones_tools.corpus.synth import SynthConfig


class TestCatalogSpec:
    def test_every_shipped_instrument_is_rendered_from_a_voice_the_synthesizer_holds(self) -> None:
        voices = SynthConfig.load().voices

        instruments = CatalogSpec.load().instruments

        assert instruments
        assert all(instrument.synth in voices for instrument in instruments)
        assert all(instrument.channels for instrument in instruments)
