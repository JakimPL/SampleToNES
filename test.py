import argparse
import cProfile
import pstats
import time
from typing import Dict, List, Tuple

from configs.config import Config
from constants.enums import GeneratorClassName
from ffts.window import Window
from library.creator.creation import generate_instructions
from reconstructor.maps import GENERATOR_CLASS_MAP
from typehints.generators import GeneratorUnion
from typehints.instructions import InstructionUnion


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", "-o", default="profile_generate_instructions.prof")
    parser.add_argument("--limit", "-n", type=int, default=0)
    args = parser.parse_args()

    config = Config()
    window = Window(config.library)
    generators: Dict[GeneratorClassName, GeneratorUnion] = {
        name: GENERATOR_CLASS_MAP[name](config, name) for name in GENERATOR_CLASS_MAP
    }

    instructions: List[Tuple[GeneratorClassName, InstructionUnion]] = [
        (generator.class_name(), instruction)
        for generator in generators.values()
        for instruction in generator.get_possible_instructions()
    ]

    if args.limit > 0:
        instructions = instructions[: args.limit]

    profiler = cProfile.Profile()
    start = time.perf_counter()
    profiler.enable()
    results = generate_instructions(instructions, config.library, window, generators)
    profiler.disable()
    elapsed = time.perf_counter() - start

    profiler.dump_stats(args.out)
    stats = pstats.Stats(profiler).sort_stats("cumtime")
    stats.print_stats(50)

    print(f"Processed {len(results)} items in {elapsed:.3f}s")
    print(f"profile saved to {args.out}")


if __name__ == "__main__":
    main()
