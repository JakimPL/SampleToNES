from __future__ import annotations

from typing import Dict

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SelectorName
from sampletones_core.fft import Window
from sampletones_core.generators import GeneratorUnion
from sampletones_core.library import InstructionLibraryData
from sampletones_core.reconstructions.reconstructor.decoder import DECODERS
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker


def _worker_with_selector(
    config: Config,
    window: Window,
    channels: Dict[ChannelName, GeneratorUnion],
    library_data: InstructionLibraryData,
    selector_name: SelectorName,
) -> ReconstructorWorker:
    decoder = config.generation.decoder.model_copy(update={"selector": selector_name})
    updated_config = config.model_copy(update={"generation": config.generation.model_copy(update={"decoder": decoder})})
    return ReconstructorWorker(
        config=updated_config,
        window=window,
        channels=channels,
        library_data=library_data,
        signal_length=config.library.frame_length,
    )


class TestWorkerDecoder:
    def test_the_configured_selector_names_the_decoder(
        self,
        config: Config,
        window: Window,
        channels: Dict[ChannelName, GeneratorUnion],
        library_data: InstructionLibraryData,
    ) -> None:
        for selector_name in SelectorName:
            worker = _worker_with_selector(config, window, channels, library_data, selector_name)
            assert isinstance(worker.decoder, DECODERS[selector_name])

    def test_the_default_configuration_builds_the_decoder_it_names(self, worker: ReconstructorWorker) -> None:
        assert isinstance(worker.decoder, DECODERS[worker.config.generation.decoder.selector])


class TestWorkerMatcher:
    def test_the_matcher_scores_through_the_workers_own_machinery(self, worker: ReconstructorWorker) -> None:
        """One scorer, provider and aligner serve both the matching and everything built on it."""
        assert worker.matcher.scorer is worker.scorer
        assert worker.matcher.candidate_provider is worker.candidate_provider
        assert worker.matcher.phase_aligner is worker.phase_aligner
        assert worker.matcher.config is worker.config
