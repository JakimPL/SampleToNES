from dataclasses import dataclass, field

from sampletones_core.performance import ChannelPerformance

from ..protocol import ChannelGeneratorProtocol


@dataclass
class ChannelState:
    """One channel of the synthesiser: the voice filling its ticks, beside what it carries.

    The pattern state is the engine's own (:class:`~sampletones_core.performance.state.ChannelPerformance`),
    so what a channel is sounding, how far into it, and at what transpose and volume are read
    the same here as anywhere else a song is played out. The generator is what makes this the
    audible reading of it: it holds the timer phase across ticks and rows, so a note sustained
    over several rows keeps one continuous waveform.

    Attributes:
        generator: The synthesiser filling the channel's ticks.
        performance: What the channel carries from row to row.
    """

    generator: ChannelGeneratorProtocol
    performance: ChannelPerformance = field(default_factory=ChannelPerformance)

    def reset(self) -> None:
        """Returns the channel to silence at full volume, as a song starts it.

        The generator is kept, since it is built from the rates in force rather than from
        anything a song reaches.
        """
        self.performance.reset()
