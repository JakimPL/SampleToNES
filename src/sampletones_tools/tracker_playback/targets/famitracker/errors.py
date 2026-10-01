from sampletones_tools.tracker_playback.targets.protocol import PlaybackError


class FamiTrackerError(PlaybackError):
    """FamiTracker could not play a project: it or Wine is missing, its export failed, or its NSF failed to run."""
