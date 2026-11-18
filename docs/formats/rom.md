# NES ROM export format

This document is the reference for the `.nes` files _SampleToNES_ writes: a cartridge image the console,
an emulator or a flash cartridge runs. Read it before changing how a cartridge is written or what its
screen shows. The song inside is the same song block an [NSF](nsf.md) carries, played by the same driver;
[the player](../development/player.md) explains how both are built and verified.

A cartridge carries three things an `.nsf` does: the driver, the song and the text the song is listed
under. It adds the shell, the code that starts the console, draws the player screen and answers the
controller, and the tiles the screen is drawn with.

Every constant named here has a counterpart under `sampletones_player/specification/`.

## A. The file

```
+0          iNES header, 16 bytes
+16         the program, 32 KB, mapped at $8000-$FFFF
+32784      the tiles, 8 KB: the screen's pattern table, then the sprites'
```

The header names the plainest board, NROM-256 (mapper 0): two 16 KB program units and one 8 KB tile unit,
with every flag byte zero. The file is 40,976 bytes.

## B. The program

```
$8000            the driver, byte for byte the one an NSF carries (init $8000, play $8003)
$8000 + driver   the song block, byte for byte the one an NSF carries
...              $FF up to the shell
$10000 - shell   the shell: the program block, its code and its tables
$FFFA            the vectors: frame interrupt, power-on, interrupt
```

The driver and the song stand where an NSF puts them, so the two files differ only around them. The song
has the room between the driver and the shell, about 30 KB.

The shell is assembled once with the driver sources and committed as `shell.bin`, so writing a cartridge
needs no assembler. It reads the driver's memory by name, which keeps its readings tied to the driver it
was built with, and it opens with the address it was built to find the song at. The writer refuses a
shell built for another driver.

## C. The program block

The exporter fills the first bytes of the shell with what the screen shows about the song. Numbers are
little-endian; times are four digits, minutes then seconds, each 0-9.

| Offset | Size | Field |
|---|---|---|
| `0x00` | 2 | song address the shell was built with |
| `0x02` | 20 | title, one character per cell |
| `0x16` | 20 | artist |
| `0x2A` | 28 | copyright |
| `0x46` | 4 | total time |
| `0x4A` | 3 | total frames: the frames the song takes to run past its end the first time |
| `0x4D` | 3 | progress step: pixels the progress bar grows by a frame, in 1/65536ths |
| `0x50` | 3 | loop frames: the frames from the loop tick to the end, or 0 for a song that ends |
| `0x53` | 4 | loop time |
| `0x57` | 2 | loop second: the part of a second the clock holds at the loop, in 1/65536ths |
| `0x59` | 3 | loop progress: where the progress bar stands at the loop, in 1/65536ths of a pixel |

The text is plain ASCII, the codes the screen's font draws at. A letter outside ASCII is written as its
base letter (`ż` as `z`, `ł` as `l`), and any other character as `?`.

The shell counts the song's time itself, once a frame. It adds 1,090/65,536 of a second (one NTSC frame)
to its clock and the progress step to the bar, and counts the total frames down. When they run out, a
song that repeats takes up the loop's time, progress and frames, and one that ends holds the clock.
Python works out every figure with the same arithmetic, so the total time is the time the frames add up
to.

## D. A frame

Each frame interrupt does the same work in the same number of cycles:

1. Sends the 64 sprites to the video chip.
2. Writes six runs of cells: the playing state and the time (7), the progress bar (25), and two channels
   (18 and 4 cells each). The pulses are written on one frame and the triangle and the noise on the next.
3. Calls the driver's play routine, unless the song is paused, and moves the clock on.

Screen work ends about 1,950 cycles into the 2,273-cycle vertical blank, and the driver is entered at the
same cycle of every frame, so the cartridge writes the sound registers as steadily as an NSF player.

Between frames the shell reads the controller and composes the next frame's cells from the driver's
memory: each channel's level, duty, pitch index and noise period.

## E. The controller

| Button | What it does |
|---|---|
| **START** | Pauses and resumes. A pause writes volume 0 to the pulses and the noise and silences the triangle's counter; the driver sounds them again with the next tick it writes |
| **SELECT** | Starts the song over, from cleared driver memory, as a cartridge just switched on |

## F. Limits

- The song has about 30 KB; a longer one is refused with the room it needed. A larger board with bank
  switching is a separate change to the driver and the song block.
- The cartridge runs at the NTSC rate. A song at a rate that divides 60 or is a multiple of it moves on
  the same frames throughout and runs 0.16% fast ([the step](nsf.md#b1-the-header)); the clock on
  the screen shows the time that passes. A PAL console plays the cartridge about 17% slower and a little
  over a semitone lower.
- The screen shows one song. The title and the artist hold 20 characters, the copyright 28.
