from sampletones_shared.logger import logger

from ..protocol import AudioDriverProtocol
from ..unstarted import UnstartedDriver
from .driver import PyAudioDriver


def start_portaudio() -> AudioDriverProtocol:
    """Starts PortAudio, or the backend listing no device where PortAudio refuses to start.

    PortAudio starts every host API it was built with, and one that reaches no server it needs fails
    the start as a whole: a PortAudio built with a PulseAudio host API refuses to start on a machine
    running no PulseAudio server, ALSA included. The application then plays nothing and says so, as
    on a machine offering no device, and the next refresh starts PortAudio again.

    Returns:
        AudioDriverProtocol: The started backend, or :class:`UnstartedDriver` where PortAudio refused.
    """
    try:
        return PyAudioDriver()
    except OSError as error:
        logger.warning(f"The audio system refused to start, so no sound can play: {error}")
        return UnstartedDriver()
