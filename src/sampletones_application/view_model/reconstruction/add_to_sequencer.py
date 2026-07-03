from pydantic import BaseModel


class AddToSequencerViewModel(BaseModel, frozen=True):
    """Renders the reconstruction panel's "Add to Sequencer" control.

    The action adds the loaded reconstruction to the open project as a sample. It is
    available while a reconstruction is loaded, a project is open, and that
    reconstruction is not already held by the project. When it is already held, the
    control stays disabled and surfaces the explanatory hint as a visual cue.
    """

    reconstruction_loaded: bool
    project_open: bool
    already_in_sequencer: bool

    @property
    def enabled(self) -> bool:
        return self.reconstruction_loaded and self.project_open and not self.already_in_sequencer

    @property
    def show_already_in_sequencer_hint(self) -> bool:
        return self.reconstruction_loaded and self.already_in_sequencer
