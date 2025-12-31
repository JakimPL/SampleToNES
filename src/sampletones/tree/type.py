from enum import StrEnum


class NodeType(StrEnum):
    ROOT = "root"
    DIRECTORY = "directory"
    FILE = "file"
    LIBRARY = "library"
    GROUP = "group"
    GENERATOR = "generator"
    INSTRUCTION = "instruction"
