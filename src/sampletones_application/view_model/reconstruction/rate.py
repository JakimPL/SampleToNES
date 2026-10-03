from enum import StrEnum


class RateLock(StrEnum):
    """Why the open reconstruction's NES frequency is locked, which the Source card explains.

    A sample of the project runs at the rate the project sets. A reconstruction with no file keeps
    its rate until it is saved to one.
    """

    PROJECT_SAMPLE = "project_sample"
    NO_FILE = "no_file"
