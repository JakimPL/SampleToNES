from dataclasses import dataclass
from typing import Optional, Tuple

import pytest

from sampletones_shared.utils.agreement import Agreement
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

_ABSENT = -1
_MIXED = -2


class TestAgreementOutcomes(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class OutcomeCase(BaseRegularTestCase):
        values: Tuple[Optional[int], ...]
        expected_absent: bool
        expected_unanimous: bool
        expected_mixed: bool
        expected_resolved: Optional[int]

    test_cases = (
        OutcomeCase(
            label="no_sources_are_absent",
            values=(),
            expected_absent=True,
            expected_unanimous=False,
            expected_mixed=False,
            expected_resolved=_ABSENT,
        ),
        OutcomeCase(
            label="one_source_is_unanimous",
            values=(5,),
            expected_absent=False,
            expected_unanimous=True,
            expected_mixed=False,
            expected_resolved=5,
        ),
        OutcomeCase(
            label="repeated_value_is_unanimous",
            values=(5, 5, 5),
            expected_absent=False,
            expected_unanimous=True,
            expected_mixed=False,
            expected_resolved=5,
        ),
        OutcomeCase(
            label="differing_values_are_mixed",
            values=(5, 7),
            expected_absent=False,
            expected_unanimous=False,
            expected_mixed=True,
            expected_resolved=_MIXED,
        ),
        OutcomeCase(
            label="every_source_absent_is_unanimous_on_absence",
            values=(None, None),
            expected_absent=False,
            expected_unanimous=True,
            expected_mixed=False,
            expected_resolved=None,
        ),
        OutcomeCase(
            label="absence_beside_a_value_is_mixed",
            values=(None, 5),
            expected_absent=False,
            expected_unanimous=False,
            expected_mixed=True,
            expected_resolved=_MIXED,
        ),
    )

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_outcome_flags_and_resolution(self, case: OutcomeCase) -> None:
        agreement: Agreement[Optional[int]] = Agreement.collapse(case.values)

        assert agreement.is_absent is case.expected_absent
        assert agreement.is_unanimous is case.expected_unanimous
        assert agreement.is_mixed is case.expected_mixed
        assert agreement.resolve(absent=_ABSENT, mixed=_MIXED) == case.expected_resolved


class TestAgreementValue:
    def test_unanimous_absence_reports_absence_as_the_agreed_value(self) -> None:
        """The outcome and the agreed value are read apart, so ``None`` can be what they share."""
        agreement: Agreement[Optional[int]] = Agreement.collapse((None, None))

        assert agreement.is_unanimous
        assert agreement.value is None

    def test_no_sources_have_no_agreed_value(self) -> None:
        with pytest.raises(ValueError):
            Agreement.collapse(()).value

    def test_differing_sources_have_no_agreed_value(self) -> None:
        with pytest.raises(ValueError):
            Agreement.collapse((5, 7)).value

    def test_order_of_sources_leaves_the_agreement_equal(self) -> None:
        assert Agreement.collapse((5, 7)) == Agreement.collapse((7, 5))
