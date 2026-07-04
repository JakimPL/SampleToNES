from pathlib import Path
from typing import Any, Callable, Dict, Optional, Protocol, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import (
    GlobalMessageElements,
    TreeElements,
)
from sampletones_application.categories.elements.instructions import (
    InstructionsLibraryElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.general import (
    SUF_PANEL_LEFT,
    TAG_GLOBAL_TAB_INSTRUCTIONS,
)
from sampletones_application.constants.instructions import (
    TAG_INSTRUCTIONS_LIBRARY_BUTTON_CANCEL_GENERATION,
    TAG_INSTRUCTIONS_LIBRARY_BUTTON_GENERATE_LIBRARY,
    TAG_INSTRUCTIONS_LIBRARY_BUTTON_REFRESH_LIBRARIES,
    TAG_INSTRUCTIONS_LIBRARY_GROUP_CONTROLS,
    TAG_INSTRUCTIONS_LIBRARY_GROUP_GENERATE,
    TAG_INSTRUCTIONS_LIBRARY_GROUP_GENERATING,
    TAG_INSTRUCTIONS_LIBRARY_GROUP_IDLE,
    TAG_INSTRUCTIONS_LIBRARY_GROUP_TREE,
    TAG_INSTRUCTIONS_LIBRARY_PANEL,
    TAG_INSTRUCTIONS_LIBRARY_PROGRESS,
    TAG_INSTRUCTIONS_LIBRARY_TEXT_STATUS,
    TAG_INSTRUCTIONS_LIBRARY_TOOLTIP_GENERATE,
    TAG_INSTRUCTIONS_LIBRARY_TREE,
    TAG_INSTRUCTIONS_LIBRARY_WINDOW_TREE,
)
from sampletones_application.layout.behavior import TreeBehavior
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.context_menu import context_menu
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.tree.colors import TreeColors
from sampletones_application.ui.elements.tree.handler import NodeHandler
from sampletones_application.ui.elements.tree.protocol import TreeLogicProtocol
from sampletones_application.ui.elements.tree.state import TreeNodeState
from sampletones_application.ui.elements.tree.tree import GUITreePanel
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.utils.gui.tooltip import attach_disabled_tooltip
from sampletones_application.utils.thread import concurrent
from sampletones_application.view_model.instruction.library import LibraryPanelViewModel
from sampletones_core.constants.enums import LibraryGeneratorName
from sampletones_core.library import InstructionLibraryKey
from sampletones_core.structures.tree import (
    GeneratorNode,
    LibraryNode,
    NodeType,
    Tree,
    TreeNode,
    TreeTraversal,
    traverse,
)
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import MessageCallback, VoidCallback


class LibraryLogicProtocol(Protocol):
    """The library-catalogue contract ``GUIInstructionsLibraryPanel`` drives.

    Typing the collaborator structurally keeps the panel bound to the queries
    its rendering needs — the current-library check runs per node, and the
    rebuild and status steps run inside the panel's concurrent rebuild job —
    while the owning coordinator constructs the real logic object and injects
    it.
    """

    @property
    def tree(self) -> Tree: ...

    @property
    def current_library_key(self) -> Optional[InstructionLibraryKey]: ...

    def rebuild_tree(self) -> None: ...

    def update_status(self) -> None: ...

    def get_path(self, key: InstructionLibraryKey) -> Path: ...


class GUIInstructionsLibraryPanel(GUITreePanel):
    def __init__(
        self,
        library_logic: LibraryLogicProtocol,
        tree_logic: TreeLogicProtocol,
        shortcut_manager: ShortcutManager,
        *,
        tree_behavior: TreeBehavior,
        language_manager: LanguageManager,
        colors: TreeColors,
        is_operation_active: Callable[[], bool],
    ) -> None:
        self._library_logic = library_logic
        self._tree_behavior = tree_behavior

        self._is_operation_active = is_operation_active

        self.on_refresh_requested: Optional[VoidCallback] = None
        self.on_generate_requested: Optional[VoidCallback] = None
        self.on_cancel_generation: Optional[VoidCallback] = None
        self.on_library_selected: Optional[Callable[[InstructionLibraryKey], None]] = None
        self.on_generator_selected: Optional[Callable[[InstructionLibraryKey, LibraryGeneratorName], None]] = None

        self._lbl_generate = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.LABEL,
            InstructionsLibraryElements.GENERATE_LIBRARY_BUTTON,
        ]
        self._tooltip_generate_disabled = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.MESSAGE,
            GlobalMessageElements.OPERATION_IN_PROGRESS,
        ]
        self._lbl_refresh = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.LABEL,
            InstructionsLibraryElements.REFRESH_LIBRARIES_BUTTON,
        ]
        self._lbl_cancel = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.LABEL,
            InstructionsLibraryElements.CANCEL_GENERATION_BUTTON,
        ]
        self._lbl_libraries = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.LABEL,
            InstructionsLibraryElements.LIBRARIES_TEXT,
        ]
        self._lbl_available_libraries = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.LABEL,
            InstructionsLibraryElements.AVAILABLE_LIBRARIES_TEXT,
        ]
        self._lbl_ctx_load_generator = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.LABEL,
            InstructionsLibraryElements.CONTEXT_LOAD_GENERATOR,
        ]
        self._lbl_ctx_load_library = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.LABEL,
            InstructionsLibraryElements.CONTEXT_LOAD_LIBRARY,
        ]
        self._msg_status_node_generator = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.STATUS_NODE_GENERATOR,
        ]
        self._msg_status_node_library = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.STATUS_NODE_LIBRARY,
        ]

        self._node_handlers: Dict[NodeType, NodeHandler]

        super().__init__(
            self._library_logic.tree,
            tag=TAG_INSTRUCTIONS_LIBRARY_PANEL,
            parent=f"{TAG_GLOBAL_TAB_INSTRUCTIONS}{SUF_PANEL_LEFT}",
            tree_tag=TAG_INSTRUCTIONS_LIBRARY_TREE,
            tree_logic=tree_logic,
            shortcut_manager=shortcut_manager,
            search_label=language_manager[
                Page.GLOBAL,
                Panel.BROWSER,
                TextType.LABEL,
                TreeElements.SEARCH,
            ],
            language_manager=language_manager,
            colors=colors,
        )

    def _setup_handlers(self) -> None:
        self._node_handlers = {
            NodeType.LIBRARY: NodeHandler(
                tag=self._get_node_handler_tag(NodeType.LIBRARY),
                node_type=NodeType.LIBRARY,
                item_click_callback=self._on_library_node_clicked,
                status_bar_callback=self._create_status_bar_message_function_for_instructions_node(),
            ),
            NodeType.GENERATOR: NodeHandler(
                tag=self._get_node_handler_tag(NodeType.GENERATOR),
                node_type=NodeType.GENERATOR,
                item_click_callback=self._on_generator_node_clicked,
                status_bar_callback=self._create_status_bar_message_function_for_instructions_node(),
            ),
        }

        super()._setup_handlers()

    def create_panel(self) -> None:
        self._setup_handlers()
        with dpg.child_window(
            tag=self.tag,
            width=self.width,
            height=self.height,
            parent=self.parent,
            border=False,
        ):
            self._create_section_text()
            self._create_library_status()
            self._create_library_controls()
            self._create_library_tree()

    def _create_section_text(self) -> None:
        section_text = dpg.add_text(self._lbl_libraries)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_library_status(self) -> None:
        dpg.add_separator()
        text = dpg.add_text("", tag=TAG_INSTRUCTIONS_LIBRARY_TEXT_STATUS)
        FontRegistry.bind_to_item(text, Font.REGULAR_SMALL)

    def _create_library_controls(self) -> None:
        with dpg.group(tag=TAG_INSTRUCTIONS_LIBRARY_GROUP_CONTROLS):
            with dpg.group(tag=TAG_INSTRUCTIONS_LIBRARY_GROUP_IDLE):
                GUIButton(
                    tag=TAG_INSTRUCTIONS_LIBRARY_BUTTON_REFRESH_LIBRARIES,
                    label=self._lbl_refresh,
                    width=-1,
                    callback=self._on_refresh_clicked,
                )
                with dpg.group(tag=TAG_INSTRUCTIONS_LIBRARY_GROUP_GENERATE):
                    GUIButton(
                        tag=TAG_INSTRUCTIONS_LIBRARY_BUTTON_GENERATE_LIBRARY,
                        label=self._lbl_generate,
                        width=-1,
                        callback=self._on_generate_clicked,
                        font=Font.BOLD,
                    )
                attach_disabled_tooltip(
                    TAG_INSTRUCTIONS_LIBRARY_GROUP_GENERATE,
                    self._tooltip_generate_disabled,
                    tag=TAG_INSTRUCTIONS_LIBRARY_TOOLTIP_GENERATE,
                )
            with dpg.group(tag=TAG_INSTRUCTIONS_LIBRARY_GROUP_GENERATING, show=False):
                dpg.add_progress_bar(
                    tag=TAG_INSTRUCTIONS_LIBRARY_PROGRESS,
                    width=-1,
                    default_value=0.0,
                )
                GUIButton(
                    tag=TAG_INSTRUCTIONS_LIBRARY_BUTTON_CANCEL_GENERATION,
                    label=self._lbl_cancel,
                    width=-1,
                    callback=self._on_cancel_clicked,
                )

    def _create_library_tree(self) -> None:
        dpg.add_separator()
        self.create_search(self.tag)
        with dpg.child_window(
            tag=TAG_INSTRUCTIONS_LIBRARY_WINDOW_TREE,
            width=-1,
            height=-1,
        ):
            with dpg.group(tag=TAG_INSTRUCTIONS_LIBRARY_GROUP_TREE):
                with dpg.tree_node(
                    label=self._lbl_available_libraries,
                    tag=self.tree_tag,
                    default_open=True,
                ):
                    pass

    def _on_refresh_clicked(self) -> None:
        self.call(self.on_refresh_requested)

    def _on_generate_clicked(self) -> None:
        self.call(self.on_generate_requested)

    def _on_cancel_clicked(self) -> None:
        self.call(self.on_cancel_generation)

    def update_view(self, view_model: LibraryPanelViewModel) -> None:
        dpg_set_value(TAG_INSTRUCTIONS_LIBRARY_TEXT_STATUS, view_model.status_text)
        dpg_configure_item(
            TAG_INSTRUCTIONS_LIBRARY_GROUP_IDLE,
            show=view_model.idle_controls_visible,
        )
        dpg_configure_item(
            TAG_INSTRUCTIONS_LIBRARY_GROUP_GENERATING,
            show=view_model.generating_controls_visible,
        )
        dpg_configure_item(
            TAG_INSTRUCTIONS_LIBRARY_BUTTON_GENERATE_LIBRARY,
            label=view_model.generate_button_label,
        )
        dpg_configure_item(
            TAG_INSTRUCTIONS_LIBRARY_PROGRESS,
            overlay=view_model.progress_overlay,
        )
        dpg_set_value(
            TAG_INSTRUCTIONS_LIBRARY_PROGRESS,
            view_model.progress_value,
        )

    def set_tree_enabled(self, enabled: bool) -> None:
        dpg_configure_item(
            TAG_INSTRUCTIONS_LIBRARY_GROUP_TREE,
            enabled=enabled,
        )
        dpg_configure_item(
            TAG_INSTRUCTIONS_LIBRARY_BUTTON_REFRESH_LIBRARIES,
            enabled=enabled,
        )
        self._apply_action_button_states()

    def refresh_action_buttons(self) -> None:
        """Re-evaluate the generate button against the live tree-lock and operation state.

        Called whenever a long operation starts or finishes. The button stays enabled only while the
        panel is unlocked and no conversion or library generation is running, leaving the rest of the
        panel usable during such an operation. The cancel button is left alone so a generation can
        always be cancelled."""
        self._apply_action_button_states()

    def _apply_action_button_states(self) -> None:
        operation_active = self._is_operation_active()
        dpg_configure_item(
            TAG_INSTRUCTIONS_LIBRARY_BUTTON_GENERATE_LIBRARY,
            enabled=not self.locked and not operation_active,
        )
        dpg_configure_item(
            TAG_INSTRUCTIONS_LIBRARY_TOOLTIP_GENERATE,
            show=operation_active,
        )

    @concurrent(wait=False, method_bound=True)
    def rebuild_tree(self) -> None:
        if self.locked:
            return

        self.lock()
        try:
            self._library_logic.rebuild_tree()
            self.build_tree()
        finally:
            self.unlock()
            self._library_logic.update_status()

    def _has_relevant_content(self, node: TreeNode) -> bool:
        return True

    @traverse(TreeTraversal.DFS)
    def _build_tree_node(
        self,
        node: TreeNode,
        state: TreeNodeState,
        **kwargs: Any,
    ) -> None:
        node_tag = self._generate_node_tag(node)
        if node.node_type == NodeType.ROOT:
            return

        if not isinstance(node, (LibraryNode, GeneratorNode)):
            return

        if isinstance(node, LibraryNode):
            state.special_node = node

        is_current = isinstance(node, LibraryNode) and self._is_current_library_node(node)
        should_expand = is_current or self._should_expand_node(node)
        leaf = isinstance(node, GeneratorNode)
        self._queue_node(
            node,
            node_tag,
            state.parent,
            leaf=leaf,
            should_expand=should_expand,
            open_on_double_click=True,
            add_node_priority=self._tree_behavior.priority_add_node,
            add_handler_priority=self._tree_behavior.priority_add_handler,
        )

        state.parent = node_tag

    def _create_status_bar_message_function_for_instructions_node(
        self,
    ) -> MessageCallback:
        def message_function(*args: Any, user_data: Tuple[TreeNode, str], **kwargs: Any) -> str:
            node, _ = user_data
            match node.node_type:
                case NodeType.LIBRARY:
                    message = self._msg_status_node_library
                case NodeType.GENERATOR:
                    parent = node.parent
                    assert isinstance(node, GeneratorNode), "Node is not a GeneratorNode"
                    assert isinstance(parent, LibraryNode), "Generator node parent is not a LibraryNode"
                    message = self._msg_status_node_generator.format(
                        generator=node.generator_name,
                        library_key=parent.library_key.filename,
                    )
                case _:
                    raise ValueError(f"Unsupported node type '{node.node_type}' for status bar message function")

            return message

        return self._create_status_bar_message_function(message_function)

    def _on_generator_node_clicked(
        self,
        sender: Sender,
        app_data: Tuple[int, int],
        user_data: Tuple[GeneratorNode, str],
    ) -> None:
        mouse_button, _ = app_data
        node, _ = user_data
        if mouse_button == dpg.mvMouseButton_Left:
            assert isinstance(node.parent, LibraryNode), "Generator node parent is not a LibraryNode"
            self.call(self.on_generator_selected, node.parent.library_key, node.generator_name)

        if mouse_button == dpg.mvMouseButton_Right:
            self._show_generator_context_menu(node)

    def _on_library_node_clicked(
        self,
        sender: Sender,
        app_data: Tuple[int, int],
        user_data: Tuple[LibraryNode, str],
    ) -> None:
        mouse_button, _ = app_data
        node, tag = user_data
        node_open = dpg.get_value(tag)
        if mouse_button == dpg.mvMouseButton_Left:
            dpg.set_value(tag, not node_open)
            if not node_open:
                self.call(self.on_library_selected, node.library_key)

        if mouse_button == dpg.mvMouseButton_Right:
            return self._show_library_context_menu(node)

        return None

    def _show_library_context_menu(self, node: LibraryNode) -> None:
        if not isinstance(node, LibraryNode) or node.node_type != NodeType.LIBRARY:
            return

        with context_menu():
            self._add_context_menu_text(node)
            self._add_context_menu_details(node)
            self._add_context_menu_path_items(self._library_logic.get_path(node.library_key))
            self._add_context_menu_library_node(node)

    def _add_context_menu_library_node(self, node: LibraryNode) -> None:
        dpg.add_separator()
        dpg.add_menu_item(
            label=self._lbl_ctx_load_library,
            callback=lambda: self.call(self.on_library_selected, node.library_key),
        )

    def _show_generator_context_menu(self, node: GeneratorNode) -> None:
        if not isinstance(node, GeneratorNode) or node.node_type != NodeType.GENERATOR:
            return

        with context_menu():
            self._add_context_menu_text(node)
            self._add_context_menu_generator_node(node)

    def _add_context_menu_generator_node(self, node: GeneratorNode) -> None:
        dpg.add_separator()
        dpg.add_menu_item(
            label=self._lbl_ctx_load_generator,
            callback=self._on_load_generator,
            user_data=node,
        )

    def _is_current_library_node(self, node: TreeNode) -> bool:
        if not isinstance(node, LibraryNode):
            return False

        return node.library_key == self._library_logic.current_library_key

    def _on_load_generator(self, sender: Sender, app_data: bool, user_data: GeneratorNode) -> None:
        assert isinstance(user_data.parent, LibraryNode), "Generator node parent is not a LibraryNode"
        self.call(self.on_generator_selected, user_data.parent.library_key, user_data.generator_name)
