from typing import Dict

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.generators.maps import CHANNEL_CLASSES
from sampletones_core.timing import TickClock

from .protocol import ChannelGeneratorProtocol
from .rates import EngineRates


class ChannelBank:
    """The generators a sound is synthesized through, one per NES channel, and the rates they are built at.

    Each generator holds the timer state that carries a note's phase across ticks. Holding the rates here
    as well is what makes following them a single decision: the generators and the tick clock are built
    from the same pair, so they agree on how long a tick is. What each channel plays belongs to whoever
    drives the bank: the song's row walk, or a live note.
    """

    def __init__(self, config: Config, rates: EngineRates) -> None:
        self._config = config
        self._rates = rates
        self._clock: TickClock = rates.clock()
        self._generators: Dict[ChannelName, ChannelGeneratorProtocol] = self._build_generators(rates)

    @property
    def clock(self) -> TickClock:
        """The samples each tick spans at the rates in force."""
        return self._clock

    def generator(self, channel_name: ChannelName) -> ChannelGeneratorProtocol:
        """The generator filling ``channel_name``'s ticks."""
        return self._generators[channel_name]

    def follow(self, rates: EngineRates) -> None:
        """Rebuilds the generators when either rate a tick is sized from changes.

        The engine consumes ``nes_frequency`` instructions a second and the audio holds
        ``sample_rate`` samples a second, so a tick spans the quotient of the two. Following the
        project's frequency keeps a row a constant real-time duration as that frequency changes,
        and following the output's rate keeps a rendered second a second wherever the audio goes.
        Pitch derives from the APU clock rather than either rate, so a change moves only the
        per-tick frame length; the generators' phase continuity resets, which is acceptable for an
        occasional settings edit.

        The tick clock follows the same pair, since it states how long one of those ticks lasts.

        Args:
            rates: The pair in force for the ticks about to be synthesized.
        """
        if rates == self._rates:
            return

        self._rates = rates
        self._clock = rates.clock()
        self._generators = self._build_generators(rates)

    def _build_generators(
        self,
        rates: EngineRates,
    ) -> Dict[ChannelName, ChannelGeneratorProtocol]:
        config = self._engine_config(rates)
        return {
            channel_name: CHANNEL_CLASSES[channel_name](
                config,
                channel_name.value,
            )
            for channel_name in ChannelName.items()
        }

    def _engine_config(self, rates: EngineRates) -> Config:
        return self._config.with_library(
            nes_frequency=rates.nes_frequency,
            sample_rate=rates.sample_rate,
        )
