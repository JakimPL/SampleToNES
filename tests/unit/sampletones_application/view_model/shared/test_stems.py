from pathlib import Path
from typing import FrozenSet

from sampletones_application.constants.sources import SourceKind
from sampletones_application.view_model.shared.stems import StemRowViewModel, StemsListViewModel
from sampletones_core.constants.enums import ChannelName

OFFERED: FrozenSet[ChannelName] = frozenset({ChannelName.PULSE1, ChannelName.NOISE})


def _row(name: str, *, heard: FrozenSet[ChannelName], offered: FrozenSet[ChannelName] = OFFERED) -> StemRowViewModel:
    return StemRowViewModel(
        key=name,
        kind=SourceKind.RECORDING,
        name=name,
        path=Path(f"/audio/{name}.wav"),
        held=(),
        channels=heard,
        partial_channels=frozenset(),
        offered_channels=offered,
        available=True,
        level=0,
        position=0,
        record_position=0,
        level_size=1,
        level_count=1,
    )


def _view(*rows: StemRowViewModel) -> StemsListViewModel:
    return StemsListViewModel.empty().model_copy(update={"rows": rows})


class TestARowHeardAlone:
    def test_the_only_row_holding_every_channel_it_offers_stands_soloed(self) -> None:
        view = _view(_row("kick", heard=OFFERED), _row("snare", heard=frozenset()))

        assert view.soloed("kick")
        assert not view.soloed("snare")

    def test_a_row_heard_on_part_of_what_it_offers_is_not_soloed(self) -> None:
        view = _view(_row("kick", heard=frozenset({ChannelName.PULSE1})), _row("snare", heard=frozenset()))

        assert not view.soloed("kick")

    def test_a_row_heard_beside_another_is_not_soloed(self) -> None:
        view = _view(_row("kick", heard=OFFERED), _row("snare", heard=frozenset({ChannelName.NOISE})))

        assert not view.soloed("kick")

    def test_a_list_holding_a_single_row_has_none_to_silence(self) -> None:
        view = _view(_row("kick", heard=OFFERED))

        assert not view.soloed("kick")

    def test_a_row_offering_no_channel_is_not_soloed(self) -> None:
        view = _view(
            _row("kick", heard=frozenset(), offered=frozenset()),
            _row("snare", heard=frozenset()),
        )

        assert not view.soloed("kick")

    def test_a_key_the_list_does_not_hold_is_not_soloed(self) -> None:
        assert not _view(_row("kick", heard=OFFERED), _row("snare", heard=frozenset())).soloed("hat")
