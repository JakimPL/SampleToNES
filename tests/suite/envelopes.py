from sampletones_application.logic.reconstruction.envelopes import HeardEnvelopes, envelopes_view
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.view_model.reconstruction.envelopes import (
    ChannelEnvelopesViewModel,
)
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection


def exported(reconstruction: Reconstruction, selection: StemSelection) -> HeardEnvelopes:
    """What the worker exports for ``selection`` of ``reconstruction``, beside that choice."""
    return HeardEnvelopes(selection=selection, channels=reconstruction.export_heard(selection))


def heard_envelopes(reconstruction: Reconstruction, selection: StemSelection) -> ChannelEnvelopesViewModel:
    """The envelopes the instruments panel draws for ``selection`` of ``reconstruction``, as a landing builds them."""
    return envelopes_view(reconstruction, exported(reconstruction, selection))


def land_envelopes(manager: ReconstructionManager) -> None:
    """Installs on ``manager`` the envelopes the opening's listening lands: the open document's, for the choice
    its listening makes.

    A case driving the manager alone has no worker to export them, so it installs them the way a
    landing does, and the panel reads them as it reads any landed envelopes.
    """
    reconstruction = manager.reconstruction
    if reconstruction is None:
        raise RuntimeError("No reconstruction is open to land the envelopes of")

    manager.adopt_envelopes(reconstruction, exported(reconstruction, manager.listening.selection))
