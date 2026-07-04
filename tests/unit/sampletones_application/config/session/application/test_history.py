import pytest
from pydantic import ValidationError

from sampletones_application.config.session.application.history import HistoryConfig


class TestBudgetBounds:
    @pytest.mark.parametrize("budget", [0, -5])
    def test_budget_below_one_is_rejected(self, budget: int) -> None:
        with pytest.raises(ValidationError):
            HistoryConfig(budget=budget)

    def test_budget_of_one_is_accepted(self) -> None:
        config = HistoryConfig(budget=1)

        assert config.budget == 1
