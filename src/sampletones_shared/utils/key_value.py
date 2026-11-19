from typing import Final, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

KEY_VALUE_SEPARATOR: Final[str] = "_"

ModelT = TypeVar("ModelT", bound=BaseModel)


def key_value_name(model: BaseModel) -> str:
    """Writes a model as the name its fields spell, ``key_value`` pairs in their declared order.

    Library files and configuration folders are named this way, so a name says the settings it was
    made under and reads back into them through :func:`parse_key_value_name`.
    """
    return KEY_VALUE_SEPARATOR.join(f"{key}{KEY_VALUE_SEPARATOR}{value}" for key, value in model.model_dump().items())


def parse_key_value_name(name: str, model_type: Type[ModelT]) -> Optional[ModelT]:
    """The model a ``key_value`` name states, where the name is exactly the one that model writes.

    The round trip is exact: the keys stand in their declared order and every value in the form
    :func:`key_value_name` writes it, so a reordered key or a value spelled otherwise (a leading
    zero, a sign) names nothing. Callers probing arbitrary file system entries leave those as they
    are.

    Args:
        name: The name read, without any extension.
        model_type: The model whose fields the name spells.

    Returns:
        Optional[ModelT]: The model, or ``None`` where the name is malformed or a value fails
        validation.
    """
    parts = name.split(KEY_VALUE_SEPARATOR)
    keys = parts[::2]
    if len(parts) != 2 * len(model_type.model_fields) or keys != list(model_type.model_fields):
        return None

    try:
        model = model_type.model_validate(dict(zip(keys, parts[1::2])))
    except ValidationError:
        return None

    return model if key_value_name(model) == name else None
