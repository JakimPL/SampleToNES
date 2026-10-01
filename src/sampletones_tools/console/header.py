from dataclasses import dataclass
from typing import Final, Self, Tuple

from sampletones_core.formats.binary import BinaryReader
from sampletones_player.specification.nsf import (
    BANKSWITCH_SIZE,
    DUAL_REGION_FLAG,
    NSF_MAGIC,
    PAL_REGION_FLAG,
    STRING_FIELD_SIZE,
)
from sampletones_tools.console.errors import NotAnNSFError

VERSION_SIZE: Final[int] = 1
STRING_FIELDS: Final[int] = 3
NTSC_MACHINE: Final[int] = 0x00
PAL_MACHINE: Final[int] = 0x01
FIRST_SONG_NUMBER: Final[int] = 1


@dataclass(frozen=True)
class NSFHeader:
    """What an NSF player reads from a file's header before it runs the file.

    Attributes:
        songs: How many songs the file holds.
        first_song: The song a player starts with, counted from 1.
        load: The address the image loads at.
        init: The routine that starts a song.
        play: The routine a player calls once per tick.
        ntsc_period: The microseconds between play calls on an NTSC machine.
        banks: The bank each 4 KB slot of ``$8000``-``$FFFF`` starts with, all zero for a file loaded whole.
        pal_period: The microseconds between play calls on a PAL machine.
        region: The machines the file plays on: the PAL flag, and the flag of a file made for both.
    """

    songs: int
    first_song: int
    load: int
    init: int
    play: int
    ntsc_period: int
    banks: Tuple[int, ...]
    pal_period: int
    region: int

    @classmethod
    def read(cls, data: bytes) -> Self:
        """Reads the header at the front of a whole NSF file, field by field as the format lays them out.

        Args:
            data: The file, header first.

        Returns:
            Self: The header.

        Raises:
            NotAnNSFError: If the file opens with something other than the NSF signature.
            TruncatedDataError: If the file ends inside the header.
        """
        reader = BinaryReader(data)
        signature = reader.read_bytes(len(NSF_MAGIC))
        if signature != NSF_MAGIC:
            raise NotAnNSFError(f"The file opens with {signature!r}, not the NSF signature {NSF_MAGIC!r}")

        reader.skip(VERSION_SIZE)
        songs = reader.read_uint8()
        first_song = reader.read_uint8()
        load = reader.read_uint16()
        init = reader.read_uint16()
        play = reader.read_uint16()
        reader.skip(STRING_FIELD_SIZE * STRING_FIELDS)
        ntsc_period = reader.read_uint16()
        banks = tuple(reader.read_bytes(BANKSWITCH_SIZE))
        pal_period = reader.read_uint16()
        region = reader.read_uint8()
        return cls(
            songs=songs,
            first_song=first_song,
            load=load,
            init=init,
            play=play,
            ntsc_period=ntsc_period,
            banks=banks,
            pal_period=pal_period,
            region=region,
        )

    @property
    def banked(self) -> bool:
        """Whether the file is read in switched banks, which a header naming any bank asks for."""
        return any(self.banks)

    @property
    def first_song_index(self) -> int:
        """The first song as the init routine is told it, counted from 0."""
        return self.first_song - FIRST_SONG_NUMBER

    @property
    def machine(self) -> int:
        """The machine the init routine is told it runs on: PAL for a file made for PAL alone, NTSC otherwise."""
        pal_only = bool(self.region & PAL_REGION_FLAG) and not self.region & DUAL_REGION_FLAG
        return PAL_MACHINE if pal_only else NTSC_MACHINE
