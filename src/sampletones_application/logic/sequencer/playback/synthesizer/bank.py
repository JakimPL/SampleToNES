from typing import Dict

from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.generators.maps import GENERATOR_CLASSES
from sampletones_core.timing import TickClock

from ..protocol import ChannelGeneratorProtocol
from .rates import EngineRates
from .state import ChannelState


class ChannelBank:
    """The channels a song sounds through, and the rates they are built at.

    One generator per NES channel, each holding the timer state that carries a note's phase across
    ticks and rows, beside the pattern state its channel has reached. Holding the rates here as
    well is what makes following them a single decision: the generators and the tick clock are
    built from the same pair, so they agree on how long a tick is.
    """

    def __init__(self, config: Config, rates: EngineRates) -> None:
        self._config = config
        self._rates = rates
        self._clock: TickClock = rates.clock()
        self._states: Dict[GeneratorName, ChannelState] = {
            generator_name: ChannelState(generator=generator)
            for generator_name, generator in self._build_generators(rates).items()
        }

    @property
    def clock(self) -> TickClock:
        """The samples each tick spans at the rates in force."""
        return self._clock

    def state(self, generator_name: GeneratorName) -> ChannelState:
        """What ``generator_name`` carries from row to row."""
        return self._states[generator_name]

    def reset(self) -> None:
        """Returns every channel to silence at full volume, as a song starts them."""
        for state in self._states.values():
            state.reset()

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
            rates: The pair in force for the row about to be rendered.
        """
        if rates == self._rates:
            return

        self._rates = rates
        self._clock = rates.clock()
        for generator_name, generator in self._build_generators(rates).items():
            self._states[generator_name].generator = generator

    def _build_generators(
        self,
        rates: EngineRates,
    ) -> Dict[GeneratorName, ChannelGeneratorProtocol]:
        config = self._engine_config(rates)
        return {
            generator_name: GENERATOR_CLASSES[generator_name](
                config,
                generator_name.value,
            )
            for generator_name in GeneratorName.items()
        }

    def _engine_config(self, rates: EngineRates) -> Config:
        return self._config.with_library(
            nes_frequency=rates.nes_frequency,
            sample_rate=rates.sample_rate,
        )
