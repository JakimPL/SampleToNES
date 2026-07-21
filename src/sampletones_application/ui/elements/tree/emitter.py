from dataclasses import dataclass
from typing import Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.layout.behavior import SchedulingBehavior
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.tree.spec import NodeSpec
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.gui.dpg import dpg_delete_children
from sampletones_application.utils.gui.staging import (
    attach_staged_item,
    create_stage,
    delete_stage,
    staged_container,
)
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import VoidCallback


@dataclass(frozen=True)
class _EmitContext:
    """State one staged emission carries across its frame-sliced batches.

    ``stage`` is the detached container the batches fill before the finished roots
    attach under ``root_tag``; ``on_finished`` runs once the emission completes.
    """

    specs: Tuple[NodeSpec, ...]
    root_tag: str
    stage: Sender
    on_finished: VoidCallback


class TreeEmitter:
    """Render a precomputed spec list into the live tree across several frames.

    The specs are created into a detached stage in budget-sized batches; each batch
    re-queues on the shared :class:`CallbackQueue` so interactive callbacks and service
    results interleave between slices. The final batch moves the finished roots under
    their live parent in one step and runs ``on_finished``.

    The caller holds the tree lock for the whole emission, so exactly one spec list is
    in flight and each emission runs to completion.
    """

    def __init__(self, *, scheduling: SchedulingBehavior) -> None:
        self._scheduling = scheduling

    def emit(
        self,
        specs: Tuple[NodeSpec, ...],
        root_tag: str,
        on_finished: VoidCallback,
    ) -> None:
        """Clear ``root_tag`` and stage the specs under it, then run ``on_finished``.

        Runs on the main thread. An empty spec list clears the tree and finishes
        immediately; a non-empty list starts the frame-sliced fill.
        """
        dpg_delete_children(root_tag)
        if not specs:
            on_finished()
            return

        context = _EmitContext(
            specs=specs,
            root_tag=root_tag,
            stage=create_stage(),
            on_finished=on_finished,
        )
        self._emit_batch(context, 0)

    def _emit_batch(self, context: _EmitContext, index: int) -> None:
        """Create one budget-sized slice of nodes into the stage, then continue or attach.

        Re-queueing the next slice at the emit priority lets interactive callbacks and
        service results run between slices.
        """
        if not dpg.does_item_exist(context.stage):
            context.on_finished()
            return

        end = min(index + self._scheduling.emit.batch_size, len(context.specs))
        with staged_container(context.stage):
            for spec in context.specs[index:end]:
                self._emit_node(spec, context.root_tag)

        if end < len(context.specs):
            CallbackQueue.add(
                self._emit_batch,
                context,
                end,
                priority=self._scheduling.emit.priority,
            )
            return

        self._attach_staged_tree(context)
        context.on_finished()

    def _emit_node(self, spec: NodeSpec, root_tag: str) -> None:
        if dpg.does_item_exist(spec.node_tag):
            return

        is_root_level = spec.parent_tag == root_tag
        if not is_root_level and not dpg.does_item_exist(spec.parent_tag):
            return

        parent: Sender = 0 if is_root_level else spec.parent_tag
        dpg.add_tree_node(
            tag=spec.node_tag,
            label=spec.label,
            parent=parent,
            default_open=spec.should_expand,
            open_on_arrow=spec.open_on_arrow,
            open_on_double_click=spec.open_on_double_click,
            leaf=spec.leaf,
            bullet=spec.leaf,
            user_data=(spec.node, spec.node_tag),
        )
        FontRegistry.bind_to_item(spec.node_tag, spec.name_font)
        ThemeRegistry.get(spec.theme_tag).bind_to_item(spec.node_tag)
        self._bind_handler(spec.node_tag, spec.handler_tag)

    def _bind_handler(self, node_tag: str, handler_tag: str) -> None:
        if dpg.does_item_exist(node_tag) and dpg.does_item_exist(handler_tag):
            dpg.bind_item_handler_registry(node_tag, handler_tag)

    def _attach_staged_tree(self, context: _EmitContext) -> None:
        """Move the finished root-level nodes under their live parent, in traversal order."""
        for spec in context.specs:
            if spec.parent_tag == context.root_tag:
                attach_staged_item(spec.node_tag, context.root_tag)

        delete_stage(context.stage)
