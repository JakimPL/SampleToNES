from typing import Final

from sampletones_shared.meta.source.bindings.environment import TypeEnvironment

ENVIRONMENT: Final[TypeEnvironment] = TypeEnvironment(
    types={
        "language_manager": "LanguageManager",
        "self._language_manager": "LanguageManager",
        "element": "MenuElements",
    }
)


class TestTypeOf:
    def test_a_stated_name_holds_its_type(self) -> None:
        assert ENVIRONMENT.type_of("element") == "MenuElements"

    def test_a_stated_attribute_holds_its_type(self) -> None:
        assert ENVIRONMENT.type_of("self._language_manager") == "LanguageManager"

    def test_a_spelling_the_environment_omits_states_nothing(self) -> None:
        assert ENVIRONMENT.type_of("absent") is None


class TestSpellingsOf:
    def test_every_holder_of_a_type_is_named(self) -> None:
        assert ENVIRONMENT.spellings_of("LanguageManager") == (
            "language_manager",
            "self._language_manager",
        )

    def test_holders_arrive_in_the_order_they_were_read(self) -> None:
        environment = TypeEnvironment(
            types={
                "second": "Manager",
                "first": "Manager",
            }
        )
        assert environment.spellings_of("Manager") == ("second", "first")

    def test_a_type_no_spelling_holds_names_nobody(self) -> None:
        assert ENVIRONMENT.spellings_of("Sequencer") == ()
