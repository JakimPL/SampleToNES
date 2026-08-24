from typing import List, Optional, Tuple

from sampletones_application.categories.context import (
    channel_label,
    context_label,
    context_text,
)
from sampletones_application.categories.elements.global_ import ContextElements
from sampletones_application.categories.hierarchy import TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.view_model.shared.footprint import SampleFootprintViewModel
from sampletones_core.constants.enums import ChannelName


class VoiceFootprintText:
    """The words a voice's byte figures are printed in, wherever a surface states them.

    The right-click menu prints a figure per line and the status bar states one sentence, so both
    read the same measurement through the same templates and a reader meets one figure for one
    voice however they ask for it.
    """

    def __init__(self, language_manager: LanguageManager) -> None:
        self._language_manager = language_manager
        self._lbl_sample_size = context_label(language_manager, ContextElements.SAMPLE_SIZE)
        self._tpl_size_bytes = context_text(language_manager, TextType.TEMPLATE, ContextElements.SIZE_BYTES)

    def size(self, byte_count: int) -> str:
        """One byte figure, as every surface prints it."""
        return self._tpl_size_bytes.format(bytes=byte_count)

    def items(
        self,
        footprint: Optional[SampleFootprintViewModel],
    ) -> List[Tuple[str, str]]:
        """The byte figures a menu prints: the voice's total, then each channel that plays.

        A channel standing by is written by no export, so it costs nothing and the figures name
        the channels that do.

        Args:
            footprint: The measurement to print, or ``None`` where the pool holds no such voice.

        Returns:
            List[Tuple[str, str]]: Each figure as the label it is printed under and its value.
        """
        if footprint is None:
            return []

        items = [(self._lbl_sample_size, self.size(footprint.total_bytes))]
        for channel_name in ChannelName.items():
            instrument_bytes = footprint.bytes_for(channel_name)
            if instrument_bytes is not None:
                items.append(
                    (
                        channel_label(self._language_manager, channel_name),
                        self.size(instrument_bytes),
                    )
                )

        return items

    def channels(self, footprint: SampleFootprintViewModel) -> List[str]:
        """The channels a voice plays, each named as every display naming a channel names it."""
        return [
            channel_label(self._language_manager, instrument.channel)
            for instrument in footprint.instruments
            if instrument.channel is not None
        ]
