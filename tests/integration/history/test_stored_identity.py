from pathlib import Path
from typing import Final

from sampletones_application.logic.history.action import HistoryAction
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.features.envelope import Envelope
from sampletones_core.project.container import ProjectContainer
from sampletones_core.project.voices.sample import Sample
from tests.suite.history.audit import fresh_fingerprint
from tests.suite.history.gestures import GESTURES_BY_LABEL, perform, write_arriving_sample
from tests.suite.history.projects import BASS, LEAD
from tests.suite.history.session import HistorySession

COPY_ENVELOPE: Final[Envelope[int]] = Envelope[int](items=(3, 2))
SHARED_NAME: Final[str] = "shared.stp"


def _edit_a_channel(
    session: HistorySession,
    sample: Sample,
    channel_name: ChannelName,
) -> None:
    """Writes a volume into one channel of ``sample`` from the Reconstructions tab."""
    session.open_voice_id(sample.id)
    session.audit.perform(
        lambda: session.instruments.handle_envelope_changed(channel_name, FeatureKey.VOLUME, COPY_ENVELOPE),
        action=HistoryAction.EDIT_RECONSTRUCTION,
        target=(sample.id,),
    )


def _last_sample(session: HistorySession) -> Sample:
    voice = list(session.project.voices)[-1]
    assert isinstance(voice, Sample)
    return voice


class TestEachSampleKeepsItsOwnDocumentThroughASave:
    """A save writes what every sample plays, so a reload gives each sample back its own document."""

    def test_an_edit_of_one_sample_survives_a_save(self, session: HistorySession) -> None:
        _edit_a_channel(session, session.sample(BASS), ChannelName.NOISE)

        session.save()

        assert session.stored_fingerprint() == session.audit.model.live.fingerprint

    def test_a_duplicate_edited_apart_from_its_original(self, session: HistorySession) -> None:
        perform(session, GESTURES_BY_LABEL["duplicate a sample"])
        _edit_a_channel(session, _last_sample(session), ChannelName.NOISE)

        session.save()

        assert session.stored_fingerprint() == session.audit.model.live.fingerprint

    def test_a_file_added_twice_and_edited_once(self, session: HistorySession) -> None:
        arriving = write_arriving_sample(session)
        for _ in range(2):
            session.audit.perform(
                lambda: session.sequencer.import_reconstruction(arriving),
                action=HistoryAction.ADD_SAMPLE,
                target=None,
            )

        _edit_a_channel(session, _last_sample(session), ChannelName.PULSE2)

        session.save()

        assert session.stored_fingerprint() == session.audit.model.live.fingerprint

    def test_a_project_whose_samples_share_a_document(
        self,
        session: HistorySession,
        tmp_path: Path,
    ) -> None:
        project = ProjectContainer.load(session.project_file)
        lead = next(voice for voice in project.voices if isinstance(voice, Sample) and voice.name == LEAD)
        twin = Sample(name=f"{LEAD} twin", reconstruction=lead.reconstruction)
        project.voices.append(twin)
        shared = tmp_path / SHARED_NAME
        ProjectContainer.save(project, shared)
        session.audit.transition(lambda: session.app._project_coordinator.load_project_safely(shared))
        _edit_a_channel(session, _last_sample(session), ChannelName.PULSE1)

        session.save()

        assert fresh_fingerprint(ProjectContainer.load(shared)) == session.audit.model.live.fingerprint
