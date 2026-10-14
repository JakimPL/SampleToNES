from sampletones_shared.exceptions import PlaybackError

from .driver import OutputStreamProtocol


def write_to_stream(stream: OutputStreamProtocol, data: bytes) -> None:
    """Hands one block of audio to the device, naming a failed write the way every playback reports it.

    The manager's own playback and a source streaming from a thread of its own both write here, so a
    reader told of a failed write reads the same words whichever source played.

    Raises:
        PlaybackError: If the device fails the write.
    """
    try:
        stream.write(data)
    except OSError as exception:
        raise PlaybackError(f"Failed to write to audio stream: {exception}") from exception


def close_stream(stream: OutputStreamProtocol) -> None:
    """Drains a stream and closes it, naming a failure the way every playback reports it.

    The stream is closed even where the device fails to drain it, so its handle goes either way.

    Raises:
        PlaybackError: If the device fails to stop or to close the stream.
    """
    try:
        try:
            stream.drain()
        finally:
            stream.close()
    except OSError as exception:
        raise PlaybackError(f"Failed to close audio stream: {exception}") from exception
