from abc import ABC, abstractmethod

from sampletones_application.utils.dpg import dpg_configure_item
from sampletones_shared.utils.callbacks import CallbackMixin


class GUIPanel(CallbackMixin, ABC):
    """Abstract base class for all DearPyGui panels.

    A ``GUIPanel`` owns a subtree of the DPG widget hierarchy rooted at
    ``self.tag``.  It is the fundamental building block of the View layer.
    Concrete panels are responsible for a cohesive portion of the UI (a settings
    form, a file browser, a progress bar area, …) and are composed by
    coordinators into larger tab layouts.

    Responsibilities:
    - Declare the DPG tag that identifies the root widget of this panel
      (``self.tag``).
    - Build the entire widget subtree in one call to ``create_panel()``.
    - Expose ``update_view(view_model)`` methods (defined by subclasses) so that
      coordinators can push new state without knowing internal widget structure.
    - Expose optional callback hooks (``on_x: Optional[Callback] = None``) for
      user actions; coordinators set these after construction.
    - Manage its own visibility (``show`` / ``hide`` / ``set_visibility``).

    Governing principles:
    - A panel holds only visual state: its tag, child widget references, and
      layout configuration.  It must not hold domain objects or application
      state.
    - DPG calls (``dpg.*``) are confined to ``create_panel()``, ``update_view``
      methods, and DPG-registered event callbacks.  They must not appear in the
      constructor or in any other public method.
    - The panel never calls coordinator or logic methods directly.  All outbound
      communication goes through the ``on_x`` callback hooks via
      ``CallbackMixin.call()``.
    - Panels tolerate ``None`` hooks until wiring is complete: construction and
      wiring are two separate phases.

    If ``init=True`` is passed to ``__init__``, ``create_panel()`` is called
    immediately, which requires the parent widget to already exist in DPG.
    Prefer passing ``init=False`` and calling ``create_panel()`` explicitly
    from within the parent's own ``create_panel()`` to control ordering.

    Dependencies (injected): tag and parent tag strings, layout dimensions,
    ``LanguageManager`` (in subclasses), layout configuration objects.
    """

    def __init__(
        self,
        tag: str,
        parent: str,
        width: int = 0,
        height: int = 0,
        init: bool = False,
    ) -> None:
        self.tag = tag
        self.parent = parent
        self.width = width
        self.height = height

        if init:
            self.create_panel()

    @abstractmethod
    def create_panel(self) -> None: ...

    def set_visibility(self, visible: bool) -> None:
        dpg_configure_item(self.tag, show=visible)

    def show(self) -> None:
        self.set_visibility(True)

    def hide(self) -> None:
        self.set_visibility(False)
