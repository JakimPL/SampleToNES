# NSF export format

This document is the reference for the `.nsf` files _SampleToNES_ writes: the file a
console or an NSF player loads, and the song block inside it that the player's own 6502
driver reads. Read it before changing anything under `sampletones_player/nsf/`,
`sampletones_player/compression/`, or the assembly under `sampletones_player/driver/`.
The design behind the format — why a song is stored this way and how the driver is held
to it — is in [the player](../development/player.md), and the compression scheme is explained
in [song compression](../concepts/compression.md); the layout itself is here.

An `.nsf` is unlike the tracker exports beside it. A [FamiTracker](famitracker.md) or
[Bitphase](bitphase.md) file describes a song to a program that already knows how to play
one; an `.nsf` carries its own player. The file therefore holds three things: a header
naming where the program loads and which routines the console calls, the assembled driver,
and the song that driver plays.

Every constant named here has a counterpart under
`sampletones_player/specification/`, and the assembly reads the same figures from
`driver/assembly/include/song.inc`. The two are held against each other by a test, so a
change made in one file and forgotten in the other is reported by name.

## A. The file

```
+0                      NSF header, 128 bytes
+128                    the assembled driver, loaded at $8000
+128 + driver length    the song block, at the address the header states
```

The header is NSF version 1: the magic `NESM\x1a`, one song, the load, init and play
addresses, three 32-byte text fields, and the NTSC play period. The text fields carry the
name of what was exported, its author and the copyright. Written by `nsf/header.py`.

The driver's entry points lead its image as a pair of jumps, so `init` answers at the load
address and `play` three bytes later whatever the driver's own length. That is what lets
the header state both addresses without assembling anything. The song follows the code
directly, which is the one address a build decides — `driver/addresses.py` reads it back
out of the linker's own labels.

The console calls `init` once and then `play` once a video frame. The header asks for the
NTSC frame period, so a player honoring the field and one driving from the frame itself
run a song at the speed it was built at.

**The program area is 32 KB**, from `$8000` upward, and the song block has whatever the
driver leaves of it. A song that outgrows that space is reported as an export failure
rather than written short.

## B. The song block

A song reaches the console as eight **token streams** — one per plane, two planes per
channel — decoded a tick at a time against a **dictionary** of phrases and a **timer
table** of pitches. Every offset below is a `uint16` counted from the block's own first
byte, so the whole block plays from wherever the file loads it.

```
+0      header
+43     timer table
        phrase table:  count, then one offset per phrase
        phrase bodies: each a length byte, then its values
        eight token streams, in plane order
```

### B.1 The header

| Offset | Size | Field |
|---|---|---|
| +0 | 1 | ticks each play call advances by, whole part |
| +1 | 2 | the same step's 16-bit fraction |
| +3 | 2 | the ticks the song lasts |
| +5 | 2 | the tick the song returns to, or `$FFFF` where it stops there |
| +7 | 2 | where the timer table begins |
| +9 | 2 | where the phrase table begins |
| +11 | 8×2 | where each plane's stream begins |
| +27 | 8×2 | where each plane's stream is re-entered once the song comes round |

All fields are little-endian, and the header runs to `SONG_HEADER_SIZE` bytes.

**The step is how one data set plays at every rate.** A reconstruction advances its
envelopes at whatever rate it was built at, and the console calls `play` at the video
frame rate. The step is the first measured against the second, held as a whole byte and a
16-bit fraction; the driver adds it to an accumulator each call and advances the streams
by the whole ticks that fall out. A song slower than the play rate stands still on the
calls between its ticks, and a faster one advances several.

### B.2 The timer table

The table holds the timer register value every pitch sounds at: the low byte of each
pitch, in pitch order, then the high byte of each. One pointer reaches both halves, which
is what the driver's lookup takes advantage of.

A plane names a pitch as its **index** — the distance above the lowest pitch the tuning
covers — rather than as a divider. Pitches beyond the divider's range share the timer they
clamp to, and the lowest pitch sounding a timer stands for the whole group.

The table is written from the tuning the exported work was built at, computed by the very
function the reconstruction's own generators render from.

### B.3 The dictionary

```
count               1 byte, how many phrases the table holds
offsets             one uint16 per phrase, in id order
bodies              each phrase: a length byte, then its values
```

A **phrase** is a run of values a plane plays, stored at the pitch it was found at. Its
position in the table is its **id**, and the ids that ride inside a token's opcode are the
cheap ones, so the phrases a song leans on hardest are listed first.

A song's phrases come from two places: the samples it plays, each offering the planes it
writes, and a search over whatever those leave uncovered. Both are weighed the same way —
a phrase keeps its entry by sparing the streams more bytes than the entry costs.

### B.4 The token streams

Each plane is a byte sequence written as tokens. The opcode's top two bits name the kind
and the low six carry its operand:

```
00cccccc                 hold the value the plane reached, for c+1 ticks
01nnnnnn b0..bn          the n+1 bytes that follow, one per tick
10pppppp cccccccc        phrase p, for c+1 ticks
11pppppp cccccccc tt     phrase p, for c+1 ticks, every value plus tt
```

`p == $3F` escapes: the phrase's id is the byte that follows, which reaches every id in
the table while the low ones stay a byte cheaper. The shift `tt` is **added within the
byte**, wrapping — one addition on the 6502, and the same one the encoder agrees with.

**A token's count is a duration, and it may run past the phrase.** Past its last value the
plane holds that value onward, which is how a note whose envelope has finished keeps
sounding; a count short of the body cuts the note off. One entry therefore serves every
length a figure is played at, and — with the shift — every pitch.

### B.5 Where a song comes round

A song that repeats re-enters its streams partway through, so the tick it returns to
begins a token on every plane, and that token names its values outright rather than
leaning on the value the plane had reached. Coming round is then a matter of pointing each
plane at the byte the header states and clearing what it was playing.

## C. What the planes hold

The planes are written in this order, and each pair belongs to one channel:

| Plane | Carries | Reaches |
|---|---|---|
| pulse 1 control | duty cycle and volume | `$4000` |
| pulse 1 value | pitch index | `$4002`, `$4003` |
| pulse 2 control | duty cycle and volume | `$4004` |
| pulse 2 value | pitch index | `$4006`, `$4007` |
| triangle control | linear counter | `$4008` |
| triangle value | pitch index | `$400A`, `$400B` |
| noise control | volume | `$400C` |
| noise value | period and mode | `$400E` |

Splitting a channel's registers apart is what gives each plane something to repeat: a
volume envelope and a pitch line are separate series that turn over at their own rates.

**A timer's high half reaches the register only where it differs from the last one
written.** Storing it restarts a pulse waveform and reloads the triangle's counter, so a
channel holding one pitch across a rest keeps its phase running the way a rendered channel
does.

## D. Limits

| Limit | Value |
|---|---|
| Program area | 32 KB from `$8000`, less the driver |
| Song length | as many ticks as the streams fit in |
| Offsets within the block | `uint16` |
| Ticks one hold or literal covers | up to `MAX_HOLD_TICKS` / `MAX_LITERAL_BYTES` |
| Ticks one phrase token covers | up to `MAX_PHRASE_TICKS` |
| Values one phrase holds | up to `MAX_PHRASE_LENGTH` |
| Phrases one dictionary holds | up to `MAX_PHRASE_IDS` |

A song reaching past the space behind the driver, or past what an offset field states,
raises `SongTooLargeError` naming the part that overflowed. A project offering more
phrases than a dictionary holds keeps the ones sparing the streams most, and says so.
