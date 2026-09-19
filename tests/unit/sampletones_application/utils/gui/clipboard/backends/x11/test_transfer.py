from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Final, List, Mapping, Optional, Tuple

import pytest

from sampletones_application.utils.gui.clipboard.backends.x11.connection import (
    PropertyNotify,
    PropertyValue,
    SelectionEvent,
    SelectionNotify,
)
from sampletones_application.utils.gui.clipboard.backends.x11.transfer import (
    INCREMENTAL,
    NO_PROPERTY,
    NO_WINDOW,
    SelectionTransfer,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

UTF8: Final[str] = "UTF8_STRING"
LATIN1: Final[str] = "STRING"
OWNER_WINDOW: Final[int] = 0x400001
REQUESTOR_WINDOW: Final[int] = 0x600001
DEADLINE: Final[float] = 0.0
BLOCK_TEXT: Final[str] = "SampleToNES/1 order rows=1 positions=0..1\n00 03"
WIDE_TEXT: Final[str] = "Zażółć gęślą jaźń"


@dataclass(frozen=True)
class Answer:
    """How the owner answers a request for one text type: in one write, in pieces, or with silence.

    No pieces at all is a type the owner declines.
    """

    pieces: Tuple[bytes, ...] = ()
    incremental: bool = False
    silent_after: Optional[int] = None


class ScriptedOwner:
    """The X server and the application holding the clipboard, answering from a script.

    It answers the way an ICCCM owner does: a property written and announced before the
    notification naming it, and a text sent in pieces written a piece at a time, each once the
    requestor has taken the one before. Events it has no more of mean the deadline passed.
    """

    def __init__(self, answers: Mapping[str, Answer], *, owner: int = OWNER_WINDOW) -> None:
        self.answers = answers
        self.owner = owner
        self.asked: List[str] = []
        self._atoms: Dict[str, int] = {}
        self._events: Deque[SelectionEvent] = deque()
        self._properties: Dict[int, PropertyValue] = {}
        self._pieces: Deque[bytes] = deque()
        self._pieces_sent: int = 0
        self._answer: Answer = Answer()

    def atom(self, name: str) -> int:
        return self._atoms.setdefault(name, len(self._atoms) + 1)

    def selection_owner(self, selection: int) -> int:
        return self.owner

    def create_requestor(self) -> int:
        return REQUESTOR_WINDOW

    def convert_selection(
        self,
        *,
        requestor: int,
        selection: int,
        target: int,
        landing: int,
    ) -> None:
        name = self._name(target)
        self.asked.append(name)
        self._answer = self.answers.get(name, Answer())
        if self._answer.silent_after == 0:
            return

        if not self._answer.pieces:
            self._events.append(SelectionNotify(requestor=requestor, landing=NO_PROPERTY))
            return

        if self._answer.incremental:
            self._pieces = deque(self._answer.pieces + (b"",))
            self._write(landing, PropertyValue(value_type=self.atom(INCREMENTAL), data=b"\x00\x00\x10\x00"))
        else:
            self._write(landing, PropertyValue(value_type=target, data=self._answer.pieces[0]))

        self._events.append(SelectionNotify(requestor=requestor, landing=landing))

    def take_property(self, window: int, atom: int) -> PropertyValue:
        value = self._properties.pop(atom, PropertyValue(value_type=0, data=b""))
        self._events.append(PropertyNotify(window=window, atom=atom, new_value=False))
        if self._pieces and self._answer.silent_after != self._pieces_sent:
            self._pieces_sent += 1
            self._write(atom, PropertyValue(value_type=self.atom(UTF8), data=self._pieces.popleft()))

        return value

    def next_event(self, deadline: float) -> Optional[SelectionEvent]:
        return self._events.popleft() if self._events else None

    def _write(self, atom: int, value: PropertyValue) -> None:
        self._properties[atom] = value
        self._events.append(PropertyNotify(window=REQUESTOR_WINDOW, atom=atom, new_value=True))

    def _name(self, atom: int) -> str:
        return next(name for name, known in self._atoms.items() if known == atom)


def _split(data: bytes, *, size: int) -> Tuple[bytes, ...]:
    return tuple(data[start : start + size] for start in range(0, len(data), size))


class TestTheTextATransferReads(BaseTestSuite):
    """The owner answers in whichever way it answers, and the transfer reads the text it carried."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        answers: Mapping[str, Answer] = field(default_factory=dict)
        text: str

    test_cases = (
        TestCase(
            label="text_written_as_utf8",
            answers={UTF8: Answer(pieces=(WIDE_TEXT.encode("utf-8"),))},
            text=WIDE_TEXT,
        ),
        TestCase(
            label="latin1_from_an_owner_declining_utf8",
            answers={LATIN1: Answer(pieces=("café".encode("latin-1"),))},
            text="café",
        ),
        TestCase(
            label="a_long_text_in_pieces_split_inside_a_character",
            answers={UTF8: Answer(pieces=_split(WIDE_TEXT.encode("utf-8"), size=3), incremental=True)},
            text=WIDE_TEXT,
        ),
        TestCase(
            label="an_owner_declining_every_text_type",
            answers={},
            text="",
        ),
        TestCase(
            label="an_owner_staying_silent",
            answers={UTF8: Answer(pieces=(BLOCK_TEXT.encode(),), silent_after=0)},
            text="",
        ),
        TestCase(
            label="an_owner_falling_silent_between_pieces",
            answers={UTF8: Answer(pieces=_split(BLOCK_TEXT.encode(), size=8), incremental=True, silent_after=2)},
            text="",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_transfer_reads_the_text_the_owner_carried(self, test_case: TestCase) -> None:
        owner = ScriptedOwner(test_case.answers)

        assert SelectionTransfer(owner, deadline=DEADLINE).text() == test_case.text


class TestWhatATransferAsksFor(BaseTestSuite):
    """A transfer asks for what it needs and no more, so a quiet clipboard costs nothing."""

    def test_a_clipboard_with_no_owner_reads_as_empty_unasked(self) -> None:
        owner = ScriptedOwner({UTF8: Answer(pieces=(BLOCK_TEXT.encode(),))}, owner=NO_WINDOW)

        assert SelectionTransfer(owner, deadline=DEADLINE).text() == ""
        assert owner.asked == []

    def test_utf8_is_asked_for_first(self) -> None:
        owner = ScriptedOwner({UTF8: Answer(pieces=(BLOCK_TEXT.encode(),)), LATIN1: Answer(pieces=(b"other",))})

        assert SelectionTransfer(owner, deadline=DEADLINE).text() == BLOCK_TEXT
        assert owner.asked == [UTF8]

    def test_a_silent_owner_is_asked_once(self) -> None:
        """The deadline covers the whole conversation, so silence ends it."""
        owner = ScriptedOwner({UTF8: Answer(pieces=(BLOCK_TEXT.encode(),), silent_after=0)})

        SelectionTransfer(owner, deadline=DEADLINE).text()

        assert owner.asked == [UTF8]
