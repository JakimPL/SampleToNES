from typing import Callable, Final, Optional

import dearpygui.dearpygui as dpg
from pydantic import BaseModel

from sampletones_application.utils.gui.keyboard.modifiers import (
    CTRL,
    Modifier,
    capture_modifiers,
    modifiers_display,
)
from sampletones_application.view_model.sequencer.channels import (
    SequencerChannelsViewModel,
)
from sampletones_core.constants.enums import GeneratorName
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import VoidCallback

OnChannelCallback = Callable[[GeneratorName], None]

NOTHING_MUTED: Final[SequencerChannelsViewModel] = SequencerChannelsViewModel(muted=frozenset())
"""The mix a channel name reads before the first model arrives: every channel audible."""


class ChannelMenuLabels(BaseModel, extra="forbid", frozen=True):
    """The names the items of a channel's menu carry.

    Mute and solo each come in two spellings, one per direction, so an item states the change it
    makes to the mix rather than the switch it stands for. Each panel reads its own set from the
    language file, keeping the wording under the panel the user is looking at.
    """

    mute: str
    unmute: str
    solo: str
    unsolo: str
    mute_all: str
    unmute_all: str


def channel_tooltip(template: str) -> str:
    """Spells the solo modifier into a channel name's hover explanation.

    The combination comes from the shared keyboard vocabulary, so a tooltip names it the way every
    menu accelerator does and follows a change to that vocabulary.
    """
    return template.format(modifier="+".join(modifiers_display(CTRL)))


class ChannelSwitch:
    """A channel's name as the switch that mutes it.

    The tracker's column headers and the order table's row labels name the same four channels and
    reach the same mute set, so both hand their clicks and their menus here and stay in step. The
    owning panel supplies the hooks once; the mute set arrives with each gesture, so an item reads
    the mix as it stands the moment it is built.
    """

    def __init__(
        self,
        *,
        labels: ChannelMenuLabels,
        on_mute_toggled: OnChannelCallback,
        on_soloed: OnChannelCallback,
        on_toggled: VoidCallback,
        on_muted: VoidCallback,
        on_unmuted: VoidCallback,
    ) -> None:
        self._labels = labels
        self._on_mute_toggled = on_mute_toggled
        self._on_soloed = on_soloed
        self._on_toggled = on_toggled
        self._on_muted = on_muted
        self._on_unmuted = on_unmuted

    def click(self, sender: Sender, generator: Optional[GeneratorName]) -> None:
        """Routes a click on a channel's name: plain mutes, ``Ctrl`` solos, the master name
        switches every channel at once.

        The selectable is released as the click is handled, so a name behaves as a button that
        reports the mix through its colour, and the edit cursor stays where it is.
        """
        dpg.set_value(sender, False)
        if generator is None:
            self._on_toggled()
            return

        if Modifier.CTRL in capture_modifiers():
            self._on_soloed(generator)
        else:
            self._on_mute_toggled(generator)

    def add_menu_items(
        self,
        generator: Optional[GeneratorName],
        channels: Optional[SequencerChannelsViewModel],
    ) -> None:
        """Fills the open menu for one channel, or for the master name that stands for them all.

        Every menu ends with the all-channel pair, so the master name's menu is the shared part of
        each channel's, and either one reaches "everything" and "everything back".
        """
        mix = channels if channels is not None else NOTHING_MUTED
        if generator is not None:
            self._add_channel_items(generator, mix)
            dpg.add_separator()

        self._add_all_channels_items(mix)

    def _add_channel_items(
        self,
        generator: GeneratorName,
        mix: SequencerChannelsViewModel,
    ) -> None:
        """Offers the two gestures a click on this channel's name carries, each named for what it
        does next.

        The labels follow the channel's own state, so an item reads as the change it makes rather
        than as a switch whose direction the user infers from the table.
        """
        dpg.add_menu_item(
            label=self._labels.unmute if mix.is_muted(generator) else self._labels.mute,
            callback=lambda: self._on_mute_toggled(generator),
        )
        dpg.add_menu_item(
            label=self._labels.unsolo if mix.is_soloed(generator) else self._labels.solo,
            callback=lambda: self._on_soloed(generator),
        )

    def _add_all_channels_items(self, mix: SequencerChannelsViewModel) -> None:
        """Offers the two whole-mix moves, each enabled while it has an effect to make."""
        dpg.add_menu_item(
            label=self._labels.mute_all,
            enabled=not mix.all_muted,
            callback=self._on_muted,
        )
        dpg.add_menu_item(
            label=self._labels.unmute_all,
            enabled=mix.any_muted,
            callback=self._on_unmuted,
        )
