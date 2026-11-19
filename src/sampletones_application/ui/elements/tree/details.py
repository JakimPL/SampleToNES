from typing import List, Sequence, Tuple

from sampletones_application.categories.context import channel_label
from sampletones_application.categories.manager import LanguageManager
from sampletones_core.configs.display import (
    GENERATOR_SEPARATOR,
    format_nes_frequency,
    format_sample_rate,
    format_spectrum_method,
    short_hash,
)
from sampletones_core.constants.enums import ChannelName
from sampletones_core.library import InstructionLibraryKey
from sampletones_core.reconstructions.converter.paths import ConfigDirectoryFields
from sampletones_core.structures.tree import ConfigNode, LibraryNode, TreeNode

DetailItems = List[Tuple[str, str]]


class NodeDetails:
    """The settings a row's details list: what a library or a reconstruction directory was built with.

    Each setting reads under the label the language file gives it, so the context menu and the
    tooltip list the same lines.
    """

    def __init__(self, language_manager: LanguageManager) -> None:
        self._language_manager = language_manager
        self._sample_rate = language_manager["global.context.label.detail_sample_rate"]
        self._nes_frequency = language_manager["global.context.label.detail_nes_frequency"]
        self._spectrum_method = language_manager["global.context.label.detail_spectrum_method"]
        self._transformation_gamma = language_manager["global.context.label.detail_transformation_gamma"]
        self._window_size = language_manager["global.context.label.detail_window_size"]
        self._channels = language_manager["global.context.label.detail_channels"]
        self._configuration = language_manager["global.context.label.detail_configuration"]
        self.stems_label = language_manager["global.context.label.detail_stems"]

    def of(self, node: TreeNode) -> DetailItems:
        """The settings a library row or a configuration row states, and none for any other row."""
        match node:
            case LibraryNode():
                return self.library(node.library_key)
            case ConfigNode():
                return self.reconstruction(node.config)

        return []

    def library(self, key: InstructionLibraryKey) -> DetailItems:
        return [
            (self._sample_rate, format_sample_rate(key.sample_rate)),
            (self._nes_frequency, format_nes_frequency(key.nes_frequency)),
            (self._spectrum_method, format_spectrum_method(key.spectrum_method)),
            (self._transformation_gamma, str(key.transformation_gamma)),
            (self._window_size, str(key.window_size)),
            (self._configuration, short_hash(key.config_hash)),
        ]

    def reconstruction(self, fields: ConfigDirectoryFields) -> DetailItems:
        return [
            (self._sample_rate, format_sample_rate(fields.sr)),
            (self._nes_frequency, format_nes_frequency(fields.nf)),
            (self._spectrum_method, format_spectrum_method(fields.sm)),
            (self._transformation_gamma, str(fields.tg)),
            (self._channels, self._channel_names(fields.channels)),
            (self._configuration, short_hash(fields.ch)),
        ]

    def _channel_names(self, channels: Sequence[ChannelName]) -> str:
        """The channels a reconstruction was built with, named as every display names them."""
        return GENERATOR_SEPARATOR.join(channel_label(self._language_manager, channel) for channel in channels)
