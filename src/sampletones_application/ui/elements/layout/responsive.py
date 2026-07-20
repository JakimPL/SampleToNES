def expanded_side_width(
    base_width: int,
    viewport_width: int,
    baseline_viewport_width: int,
    side_panel_count: int,
    center_weight: int,
) -> int:
    """Widens a fixed side column as the viewport grows past the design baseline.

    A tab's centre column stretches while its side columns hold fixed widths, so the extra room a
    viewport wider than ``baseline_viewport_width`` offers is shared out with the centre taking
    ``center_weight`` shares against each side's single share. Splitting the surplus
    ``center_weight + side_panel_count`` ways and granting one share to each side keeps the centre the
    widest column while the sides breathe on large displays. At the baseline the column sits at its
    configured ``base_width`` and grows only as surplus appears above it.
    """
    surplus = viewport_width - baseline_viewport_width
    total_weight = center_weight + side_panel_count
    expansion = max(0, round(surplus / total_weight))
    return base_width + expansion


def stacked_graph_height(
    base_height: int,
    viewport_height: int,
    baseline_viewport_height: int,
    graph_count: int,
    max_stack_height: int,
) -> int:
    """Grows each graph of a vertical stack as the viewport grows past the lowest-resolution baseline.

    At ``baseline_viewport_height`` — the smallest supported window — the stacked graphs sit at
    ``base_height`` and together fill their column. The extra room a taller viewport offers is shared
    equally across the ``graph_count`` graphs, so the stack keeps filling as the window grows, until the
    graphs together reach ``max_stack_height``; from there each graph holds at its
    ``max_stack_height // graph_count`` cap and the surplus stays free.
    """
    surplus = viewport_height - baseline_viewport_height
    expansion = max(0, round(surplus / graph_count))
    max_graph_height = max_stack_height // graph_count
    return min(base_height + expansion, max_graph_height)
