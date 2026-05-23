import os
from pathlib import Path
from typing import Union

Pathlike = Union[str, Path]
GeneralPathlike = Union[Pathlike, os.PathLike[str]]
