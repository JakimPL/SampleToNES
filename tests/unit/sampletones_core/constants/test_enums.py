from sampletones_core.constants.enums import GeneratorName, abbreviate_generator_names


class TestAbbreviateGeneratorNames:
    def test_single_generator_produces_its_abbreviation(self) -> None:
        assert abbreviate_generator_names([GeneratorName.PULSE1]) == "P"

    def test_multiple_generators_concatenates_in_order(self) -> None:
        assert "PTN" == abbreviate_generator_names(
            [
                GeneratorName.PULSE1,
                GeneratorName.TRIANGLE,
                GeneratorName.NOISE,
            ]
        )
