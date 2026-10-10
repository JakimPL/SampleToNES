from .feature import Features


def stands_by(features: Features) -> bool:
    """Whether a channel given these envelopes rests through every frame, and so stands by.

    An edit reaches a reconstruction as envelopes, which the regeneration rebuilds into the frames
    the channel plays, and a frame sounds where its volume is above zero, on every kind of channel.
    A volume left to the channel holds the level a channel starts a song at, which sounds, and a
    volume written holds one of its own items at every frame, the last or the looped one past its
    end. The envelopes therefore stand by where they describe no frame, or where every item the
    volume writes is zero, which is the reading the rebuilt frames give without rebuilding them.

    Args:
        features: The envelopes the channel is given.

    Returns:
        bool: True where no frame the envelopes describe sounds.
    """
    if not features.has_frames:
        return True

    volume = features.volume
    if not volume.written:
        return False

    return all(item == 0 for item in volume.items)
