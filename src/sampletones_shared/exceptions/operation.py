from .base import SampleToNESError


class OperationCancelled(SampleToNESError):
    """Raised when work in progress is withdrawn by whoever asked for it.

    Long operations look up between the steps they are made of and ask the caller whether the
    answer is still wanted. A caller that says no leaves the work unwound at that point, so the
    boundary that started it reports a cancelled run rather than a finished or failed one.
    """
