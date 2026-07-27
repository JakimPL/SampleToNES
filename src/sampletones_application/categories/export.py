from __future__ import annotations

from dataclasses import dataclass

from sampletones_application.categories.elements.reconstructions import (
    ReconstructionPanelElements,
    ReconstructionsInstrumentsElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager


@dataclass(frozen=True)
class ExportMessages:
    """The dialog texts an export result is reported with.

    One bundle carries every title and message the reconstruction tab needs to describe
    an export, so the coordinator resolves them once and the result handler reads them
    from a single value.

    Attributes:
        status_title: Title of the instrument export result dialog.
        wav_title: Title of the WAV export dialog and its result.
        instrument_success: Shown when one instrument reaches its file.
        instrument_truncated: Template describing what a shortened instrument carries.
        instrument_failed: Shown when one instrument export fails.
        instruments_success: Shown when a reconstruction's instruments reach their files.
        instruments_truncated: Template describing how many instruments were shortened.
        instruments_failed: Shown when a reconstruction's instrument export fails.
        wav_success: Shown when the reconstruction reaches a WAV file.
        wav_failed: Shown when the WAV export fails.
    """

    status_title: str
    wav_title: str
    instrument_success: str
    instrument_truncated: str
    instrument_failed: str
    instruments_success: str
    instruments_truncated: str
    instruments_failed: str
    wav_success: str
    wav_failed: str

    @classmethod
    def build(cls, language_manager: LanguageManager) -> ExportMessages:
        """Resolves every export text from the language manager.

        Args:
            language_manager: The source of the localized texts.

        Returns:
            ExportMessages: The bundle the export result handler reads.
        """
        return cls(
            status_title=cls._instruments_text(
                language_manager,
                TextType.TITLE,
                ReconstructionsInstrumentsElements.EXPORT_STATUS_DIALOG,
            ),
            wav_title=cls._instruments_text(
                language_manager,
                TextType.TITLE,
                ReconstructionsInstrumentsElements.EXPORT_WAV_DIALOG,
            ),
            instrument_success=cls._instruments_text(
                language_manager,
                TextType.MESSAGE,
                ReconstructionsInstrumentsElements.EXPORT_INSTRUMENT_SUCCESS,
            ),
            instrument_truncated=cls._instruments_text(
                language_manager,
                TextType.MESSAGE,
                ReconstructionsInstrumentsElements.EXPORT_INSTRUMENT_TRUNCATED,
            ),
            instrument_failed=cls._instruments_text(
                language_manager,
                TextType.MESSAGE,
                ReconstructionsInstrumentsElements.EXPORT_INSTRUMENT_FAILED,
            ),
            instruments_success=cls._instruments_text(
                language_manager,
                TextType.MESSAGE,
                ReconstructionsInstrumentsElements.EXPORT_INSTRUMENTS_SUCCESS,
            ),
            instruments_truncated=cls._instruments_text(
                language_manager,
                TextType.MESSAGE,
                ReconstructionsInstrumentsElements.EXPORT_INSTRUMENTS_TRUNCATED,
            ),
            instruments_failed=cls._instruments_text(
                language_manager,
                TextType.MESSAGE,
                ReconstructionsInstrumentsElements.EXPORT_INSTRUMENTS_FAILED,
            ),
            wav_success=language_manager[
                Page.RECONSTRUCTIONS,
                Panel.RECONSTRUCTION,
                TextType.MESSAGE,
                ReconstructionPanelElements.EXPORT_WAV_SUCCESS,
            ],
            wav_failed=language_manager[
                Page.RECONSTRUCTIONS,
                Panel.RECONSTRUCTION,
                TextType.MESSAGE,
                ReconstructionPanelElements.EXPORT_WAV_FAILED,
            ],
        )

    @staticmethod
    def _instruments_text(
        language_manager: LanguageManager,
        text_type: TextType,
        element: ReconstructionsInstrumentsElements,
    ) -> str:
        return language_manager[Page.RECONSTRUCTIONS, Panel.INSTRUMENTS, text_type, element]
