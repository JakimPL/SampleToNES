from sampletones_core.constants.enums import ChannelName


def instrument_slice_name(base_name: str, channel: ChannelName) -> str:
    """Names one channel slice of a reconstruction.

    Every export path shares this form, so a slice carries the same name whether it
    reaches a tracker as a standalone instrument file or as one entry of a project's
    instrument table. The parenthesised suffix keeps the base name readable while
    identifying the channel the slice drives.

    Args:
        base_name: The name of the reconstruction or sample the slice came from.
        channel: The NES channel the slice covers.

    Returns:
        str: The slice's name, of the form ``base (channel)``.
    """
    return f"{base_name} ({channel})"
