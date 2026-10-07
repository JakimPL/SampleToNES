from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, ClassVar, Optional

from sampletones_shared.logger import logger
from sampletones_shared.meta import NonInstantiableMeta

FailurePresenter = Callable[[Exception], None]
FailurePost = Callable[[FailurePresenter, Exception], None]
ThreadHook = Callable[[threading.ExceptHookArgs], object]


@dataclass(frozen=True)
class FailureAttachment:
    """What a running interface attached to the channel: the presenter, its post, and the hook it found.

    Attributes:
        present: Shows the reader one failure. Runs on the render thread.
        post: Hands ``present`` and the failure to the render thread.
        saved_thread_hook: The thread hook in place when the channel was attached.
    """

    present: FailurePresenter
    post: FailurePost
    saved_thread_hook: ThreadHook


class UnhandledFailures(metaclass=NonInstantiableMeta):
    """The one channel a failure no coordinator recovered from takes to reach the reader.

    Every place where control enters the application hands it what escapes the work it runs: the
    callback queue for gestures, frame callbacks and queued deliveries, the runner every executor
    worker runs its tasks through, and any other thread through the thread hook installed while a
    presenter is attached. A report is logged with its traceback, and the presenter is posted to
    the render thread, whichever thread failed. A failure on a worker while the interface is still
    being built is therefore presented by the first drain.

    The composition root attaches the presenter and the post that carries it to the render thread,
    and the teardown detaches them, so a report outside a running interface is logged alone. A
    presenter that fails is logged alone too, which ends a broken report at its own failure.

    Non-instantiable by design: like the callback queue it posts to, it is a process-wide channel.
    """

    _attachment: ClassVar[Optional[FailureAttachment]] = None

    @classmethod
    def attach(
        cls,
        present: FailurePresenter,
        *,
        post: FailurePost,
    ) -> None:
        """Shows every report through ``present``, carried to the render thread by ``post``.

        The thread hook in place is kept for what a thread lets escape beyond an ``Exception``, and
        put back once the channel is detached.

        Args:
            present: Shows the reader one failure. Runs on the render thread.
            post: Hands ``present`` and the failure to the render thread.
        """
        cls.detach()
        cls._attachment = FailureAttachment(present=present, post=post, saved_thread_hook=threading.excepthook)
        threading.excepthook = cls._escaped

    @classmethod
    def detach(cls) -> None:
        """Logs every later report alone, and puts back the thread hook the attachment found."""
        attachment = cls._attachment
        if attachment is None:
            return

        threading.excepthook = attachment.saved_thread_hook
        cls._attachment = None

    @classmethod
    def report(cls, exception: Exception, origin: str) -> None:
        """Logs ``exception`` as escaping ``origin``, and has the reader shown it.

        Args:
            exception: The failure nothing recovered from.
            origin: The log line's opening, naming where the failure escaped.
        """
        logger.error_with_traceback(exception, origin)
        attachment = cls._attachment
        if attachment is None:
            return

        attachment.post(cls._presented, exception)

    @classmethod
    def _presented(cls, exception: Exception) -> None:
        """Shows ``exception`` through the presenter attached when it runs.

        The presentation is the channel's own entry point, so a presenter that fails is logged here,
        and its failure ends there.
        """
        attachment = cls._attachment
        if attachment is None:
            return

        try:
            attachment.present(exception)
        except Exception as failure:  # pylint: disable=broad-exception-caught
            logger.error_with_traceback(failure, f"The report of {type(exception).__name__} could not be shown")

    @classmethod
    def _escaped(cls, arguments: threading.ExceptHookArgs) -> None:
        """Reports an ``Exception`` a thread let escape, and passes anything else to the saved hook."""
        match arguments.exc_value:
            case Exception() as exception:
                thread = f"The thread {arguments.thread.name}" if arguments.thread is not None else "A thread"
                cls.report(exception, f"{thread} let {type(exception).__name__} escape")
            case _ if cls._attachment is not None:
                cls._attachment.saved_thread_hook(arguments)
