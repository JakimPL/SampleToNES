from collections import deque
from dataclasses import dataclass
from typing import ClassVar, Deque, Dict, List, Optional, Tuple

from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_shared.meta import NonInstantiableMeta
from sampletones_shared.types.callback import VoidCallback


@dataclass(frozen=True)
class WaitingModal:
    """A modal window asked for while the screen belonged to another conversation.

    Attributes:
        tag: The window the request builds.
        build: What builds it, with everything the request carried.
    """

    tag: str
    build: VoidCallback


@dataclass(frozen=True)
class ModalQueueSnapshot:
    """What the line holds at one moment, for a reader watching the screen from outside it.

    Attributes:
        shown: The window standing on the screen, or ``None`` while the screen is free.
        aside: The windows standing aside for the modals they handed the screen to.
        waiting: The windows waiting for the screen, in the order they open.
        turning: Whether the line moves on in a coming frame.
    """

    shown: Optional[str]
    aside: Tuple[str, ...]
    waiting: Tuple[str, ...]
    turning: bool

    @property
    def is_settled(self) -> bool:
        """Whether the line stands still: nothing waits, nothing stands aside, and no turn is due."""
        return not self.aside and not self.waiting and not self.turning


class ModalQueue(metaclass=NonInstantiableMeta):
    """The one modal window DearPyGui shows at a time, and the modal windows waiting for the screen.

    DearPyGui shows one modal window at a time. A modal built while another one stands opens hidden,
    out of every reader's reach, and runs the answer its title-bar close gives. A modal built in the
    frame another one left in meets the same fate, since that frame still draws the one that left.

    The screen therefore belongs to one conversation at a time: a modal window, the modals it hands
    the screen to while it steps aside, and the ones its answers raise. A modal asked for from
    anywhere else, such as the report of a job that finished or a prompt raised by a gesture that
    waited, takes its place in line and opens once the conversation holding the screen has ended,
    a frame after its last window left. A window asked for again while it waits keeps its place in
    line with the newer request. The line is one for the process, as DearPyGui's context is.

    A hand-off is how a conversation keeps the screen while its windows change: what runs a frame
    after a window stepped aside or left, opening the modal that comes next or bringing the window
    back. Every call arrives on the render thread, where windows are built and deleted.
    """

    _shown: ClassVar[Optional[str]] = None
    _aside: ClassVar[List[str]] = []
    _returning: ClassVar[Dict[str, VoidCallback]] = {}
    _hand_offs: ClassVar[List[VoidCallback]] = []
    _waiting: ClassVar[Deque[WaitingModal]] = deque()
    _clearing: ClassVar[bool] = False
    _handing_off: ClassVar[bool] = False
    _turn_due: ClassVar[bool] = False

    @classmethod
    def open(cls, tag: str, build: VoidCallback) -> None:
        """Builds a modal window now where the screen is free for it, and once it is free otherwise.

        A modal a hand-off raises joins the conversation that handed it the screen, ahead of every
        modal waiting in line. Any other one waits for the conversation holding the screen to end.

        Args:
            tag: The window ``build`` builds.
            build: What builds the window.
        """
        cls._forget_waiting(tag)
        waiting = WaitingModal(tag=tag, build=build)
        if cls._shown is None and not cls._clearing and (cls._handing_off or not cls._screen_taken()):
            cls._build(waiting)
        elif cls._handing_off:
            cls._waiting.appendleft(waiting)
        else:
            cls._waiting.append(waiting)

    @classmethod
    def leave(cls, tag: str) -> None:
        """Gives up the screen a deleted window held, standing on it or stepped aside.

        A window still waiting for the screen gives up its place in line instead.
        """
        cls._forget_waiting(tag)
        cls._returning.pop(tag, None)
        if cls._shown == tag:
            cls._shown = None
            cls._clearing = True
            cls._take_a_turn()
        elif tag in cls._aside:
            cls._aside.remove(tag)
            cls._take_a_turn()

    @classmethod
    def step_aside(cls, tag: str) -> None:
        """Keeps the screen for a window that went off it, so the modal it hands over to opens next."""
        if cls._shown != tag:
            return

        cls._shown = None
        cls._aside.append(tag)
        cls._clearing = True

    @classmethod
    def come_back(cls, tag: str, reveal: VoidCallback) -> None:
        """Brings a window that stepped aside back onto the screen once the screen is free for it.

        Args:
            tag: The window that stepped aside.
            reveal: What puts the window back on screen.
        """
        if tag not in cls._aside:
            return

        cls._returning[tag] = reveal
        cls._take_a_turn()

    @classmethod
    def hand_off(cls, continuation: VoidCallback) -> None:
        """Runs ``continuation`` a frame from now as part of the conversation holding the screen.

        A modal ``continuation`` opens takes the screen ahead of every modal waiting in line.
        """
        cls._hand_offs.append(continuation)
        cls._take_a_turn()

    @classmethod
    def snapshot(cls) -> ModalQueueSnapshot:
        """What the line holds now: the window standing, the ones aside and the ones waiting."""
        return ModalQueueSnapshot(
            shown=cls._shown,
            aside=tuple(cls._aside),
            waiting=tuple(waiting.tag for waiting in cls._waiting),
            turning=cls._turn_due,
        )

    @classmethod
    def clear(cls) -> None:
        """Forgets every window, which is where a DearPyGui context that was just made starts from."""
        cls._shown = None
        cls._aside = []
        cls._returning = {}
        cls._hand_offs = []
        cls._waiting = deque()
        cls._clearing = False
        cls._handing_off = False
        cls._turn_due = False

    @classmethod
    def _screen_taken(cls) -> bool:
        """Whether a conversation holds the screen, or a window left it in the frame being drawn."""
        return cls._shown is not None or bool(cls._aside) or bool(cls._hand_offs) or cls._clearing

    @classmethod
    def _build(cls, waiting: WaitingModal) -> None:
        cls._shown = waiting.tag
        waiting.build()

    @classmethod
    def _forget_waiting(cls, tag: str) -> None:
        cls._waiting = deque(waiting for waiting in cls._waiting if waiting.tag != tag)

    @classmethod
    def _take_a_turn(cls) -> None:
        if cls._turn_due:
            return

        cls._turn_due = True
        FrameCallbackManager.set_frame_callback(cls._turn)

    @classmethod
    def _turn(cls) -> None:
        """Carries the screen a frame further: the hand-offs, then a window coming back, then the line.

        A window leaving during the turn keeps what comes after it for the next frame, since the
        frame being drawn still carries the window that left.
        """
        cls._turn_due = False
        cls._clearing = False
        cls._run_hand_offs()
        if cls._clearing or cls._shown is not None:
            return

        if cls._bring_back():
            return

        if not cls._screen_taken() and cls._waiting:
            cls._build(cls._waiting.popleft())

    @classmethod
    def _run_hand_offs(cls) -> None:
        """Runs the hand-offs due, in the order they were handed.

        A hand-off that raises keeps the ones after it for a coming frame, and the line goes on from
        there, so one failing answer leaves the screen to the rest of the conversation and the line.
        """
        hand_offs, cls._hand_offs = deque(cls._hand_offs), []
        cls._handing_off = True
        ran = False
        try:
            while hand_offs:
                hand_offs.popleft()()
            ran = True
        finally:
            cls._handing_off = False
            if not ran:
                cls._hand_offs = list(hand_offs) + cls._hand_offs
                cls._take_a_turn()

    @classmethod
    def _bring_back(cls) -> bool:
        """Puts the latest window that stepped aside and asked to come back on the screen."""
        for tag in reversed(cls._aside):
            reveal = cls._returning.pop(tag, None)
            if reveal is not None:
                cls._aside.remove(tag)
                cls._shown = tag
                reveal()
                return True

        return False
