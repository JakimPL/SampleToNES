from typing import NamedTuple


class RegisterWrite(NamedTuple):
    """One store the driver makes to an APU register.

    Attributes:
        address: The register the store lands on.
        value: The byte it carries.
    """

    address: int
    value: int
