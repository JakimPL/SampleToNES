# NSF export format

This document is the reference for the `.nsf` files _SampleToNES_ writes: the file a console or an NSF
player loads, and the song block inside it that the player's own 6502 driver reads. Read it before
changing how an `.nsf` is written or read. [The player](../development/player.md) explains why a song is
stored this way and how the driver is held to it. [Song compression](../concepts/compression.md) explains
the compression scheme. The layout is here.

An `.nsf` differs from the tracker exports beside it. A [FamiTracker](famitracker.md) or
[Bitphase](bitphase.md) file describes a song to a program that already knows how to play one, and an
`.nsf` carries its own player. The file has three parts: a header, the assembled driver, and the song the
driver plays. The header names where the program loads and which routines the console calls.

Every constant named here has a counterpart under `sampletones_player/specification/`. The assembly reads
the same figures from `sampletones_tools/player/assembly/include/song.inc`. A test holds the two against
each other, so a change made in one file and forgotten in the other is reported by name.

## A. The file

```
+0                      NSF header, 128 bytes
+128                    the assembled driver, loaded at $8000
+128 + driver length    the song block, at the address the header states
```

The header is NSF version 1. It has the magic `NESM\x1a`, one song, the load, init and play addresses,
three 32-byte text fields, and the NTSC play period. The text fields have the title, the artist and the
copyright an export sets. Each is UTF-8 ending in a NUL, so it holds `STRING_TEXT_SIZE` bytes of text, cut
on a character boundary. `nsf/information.py` does the cut, and `nsf/header.py` writes the header.

The driver's image starts with two jumps, the entry points. `init` is at the load address and `play` is
three bytes later, whatever the driver's own length. The header can therefore give both addresses without
assembling anything. The song follows the code directly. That address is the one thing a build decides,
and `driver/addresses.py` reads it back from the linker's own labels.

The console calls `init` once and then `play` once per video frame. The header asks for the NTSC frame
period. A player that honors the field and one that drives from the frame itself both run a song at the
speed it was built at.

**The program area is 32 KB**, from `$8000` upward, and the song block gets what the driver leaves of it.
A song that outgrows that space is reported as an export failure, and no shortened file is written.

## B. The song block

A song reaches the console as one **token stream** per plane. The driver decodes each stream a tick at a
time against a **dictionary** of phrases and a **timer table** of pitches. Every channel has a control
plane and a value plane, and a tone channel has a bend plane besides. Every offset below is a `uint16`
counted from the block's first byte, so the whole block plays from wherever the file loads it.

```
+0      header
+55     timer table
        phrase table:  count, then one offset per phrase
        phrase bodies: each a length byte, then its values
        one token stream per plane, in plane order
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
| +11 | `PLANE_COUNT`×2 | where each plane's stream begins, or `$FFFF` for an absent plane |
| +33 | `PLANE_COUNT`×2 | where each plane's stream is re-entered once the song comes round, or `$FFFF` for an absent plane |

All fields are little-endian, and the header runs to `SONG_HEADER_SIZE` bytes.

**The step lets one data set play at every rate.** A reconstruction advances its envelopes at the rate it
was built at, and the console calls `play` at the video frame rate. The step is the first rate measured
against the second, held as a whole byte and a 16-bit fraction. The driver adds it to an accumulator on
each call and advances the streams by the whole ticks that fall out. A song slower than the play rate
stands still on the calls between its ticks, and a faster one advances several.

### B.2 The timer table

The table has the timer register value each pitch sounds at: the low byte of each pitch in pitch order,
then the high byte of each. One pointer reaches both halves, which the driver's lookup uses.

A plane names a pitch as its **index**, the distance above the lowest pitch the tuning covers, and not as
a divider. A tick's divider is written as the index of the pitch it is counted from, beside a bend: the
steps from that pitch's own divider (section C). Pitches beyond the divider's range share the timer they
clamp to, and the lowest pitch sounding a timer represents the whole group.

The table comes from the tuning the exported work was built at, computed by the function the
reconstruction's own generators render from.

### B.3 The dictionary

```
count               1 byte, how many phrases the table holds
offsets             one uint16 per phrase, in id order
bodies              each phrase: a length byte, then its values
```

A **phrase** is a run of values a plane plays, stored at the pitch it was found at. Its position in the
table is its **id**. The ids that fit inside a token's opcode are the cheap ones, so the phrases a song
relies on most are listed first.

A song's phrases come from two places: the samples it plays, each offering the planes it writes, and a
search over whatever those leave uncovered. Both are weighed the same way. A phrase keeps its entry when it
saves the streams more bytes than the entry costs.

### B.4 The token streams

Each plane is a byte sequence of tokens. The opcode's top two bits name the kind and the low six carry
its operand:

```
00cccccc                 hold the value the plane reached, for c+1 ticks
01nnnnnn b0..bn          the n+1 bytes that follow, one per tick
10pppppp cccccccc        phrase p, for c+1 ticks
11pppppp cccccccc tt     phrase p, for c+1 ticks, every value plus tt
```

`p == $3F` is an escape: the phrase's id is the byte that follows. That reaches every id in the table
while the low ids stay a byte cheaper. The shift `tt` is **added within the byte** and wraps. That is one
addition on the 6502, and the encoder does the same addition.

**A token's count is a duration, and it may run past the phrase.** Past its last value the plane holds
that value, so a note whose envelope has finished keeps sounding. A count shorter than the body cuts the
note off. One entry therefore serves every length a figure is played at and, with the shift, every pitch.

### B.5 Where a song comes round

A song that repeats re-enters its streams partway through. The tick it returns to therefore begins a
token on every plane, and that token names its values outright instead of relying on the value the plane
had reached. A bend plane is re-entered at the value its channel's flags have reached by that tick
(section C), which begins a token of its own. Coming round then means pointing each plane at the byte the
header names and clearing what it was playing.

The tick a song returns to is the export's choice: its first tick, the first tick of an order frame, or
none. With none, the header has `$FFFF` and the song stops at its end.

## C. What the planes hold

The planes are written in this order, and each group belongs to one channel:

| Plane | Carries | Reaches |
|---|---|---|
| pulse 1 control | duty cycle and volume | `$4000` |
| pulse 1 value | pitch index, and a flag for a bent tick | `$4002`, `$4003` |
| pulse 1 bend | divider offset of each flagged tick | `$4002`, `$4003` |
| pulse 2 control | duty cycle and volume | `$4004` |
| pulse 2 value | pitch index, and a flag for a bent tick | `$4006`, `$4007` |
| pulse 2 bend | divider offset of each flagged tick | `$4006`, `$4007` |
| triangle control | linear counter | `$4008` |
| triangle value | pitch index, and a flag for a bent tick | `$400A`, `$400B` |
| triangle bend | divider offset of each flagged tick | `$400A`, `$400B` |
| noise control | volume | `$400C` |
| noise value | period and mode | `$400E` |

Splitting a channel's registers apart gives each plane something to repeat: a volume envelope and a pitch
line are separate series that turn over at their own rates.

**Every channel's planes are in every block.** A channel an export leaves out has its silent values from
the first tick to the last, which a hold covers in a few bytes. The driver therefore reads the same layout
whichever channels a song sounds.

**A plane playing zero throughout is absent.** Every plane starts at zero, so a plane that never leaves it
needs no stream. Both its header entries are `ABSENT_STREAM` (`$FFFF`), and the driver leaves it at zero
on every tick. A tone channel that never bends spends nothing on its bend plane.

**The noise channel has no bend plane.** It selects one of sixteen fixed periods, so there is no finer
grid for a bend to reach, and its block leaves the plane out.

**A timer's high half reaches the register only where it differs from the last one written.** Storing it
restarts a pulse waveform and reloads the triangle's counter. A channel holding one pitch across a rest
therefore keeps its phase running, as a rendered channel does.

**A value plane names a pitch, not a divider.** A note is written as its distance above the lowest one the
song reaches. That lets `TRANSPOSED_PHRASE` move a whole phrase by adding to it, and a divider offset
added to an index would mean nothing. A tone channel's **bend** plane carries the offset: signed bytes in
two's complement, added to the divider the value plane's note resolves to.

**A bend plane has a value only where a note bends.** A value byte's low seven bits index the pitch table.
Its top bit, `BEND_FLAG`, says the tick reads its offset from the bend plane, and an unflagged tick sounds
its pitch's own divider. The bend plane has one value per flagged tick, in order, and the driver advances
it on those ticks alone. The encoder flags each note from its first bent tick to its last, so a vibrato
passing through zero keeps the value plane still. A channel that never bends has an empty bend plane,
which is an absent one. The flag sits above every index, so a transposed phrase keeps it.

A bent frame sounds the divider its note's own divider is moved to. **The value plane names the frame's
own note**, and the bend plane holds the steps from that note's divider. A row transposes a note and keeps
its bend's steps, so a bent figure has the same bend bytes at every pitch it is played at, and one
dictionary entry serves it. A bend past the signed byte is counted from the pitch lying nearest the
divider, and a divider halfway between two pitches goes to the higher one. Those steps stay inside half
the widest gap between neighboring pitches, 57 at the default tuning, so every divider the register holds
reaches the planes.

The driver sign-extends that byte and adds it across both halves of the timer. That is the only arithmetic
it performs on a song's behalf. Python does everything that makes the sum land in range: `bent_timer`
keeps the divider within `[MIN_TIMER, MAX_TIMER]`, the rule the generators render a bent frame by. The
timer's high half therefore never exceeds three bits, never reaches the length-counter field beside them,
and never collides with the `$FF` the driver marks an unwritten shadow by.

## D. Limits

| Limit | Value |
|---|---|
| Program area | 32 KB from `$8000`, less the driver |
| Song length | as many ticks as the streams fit in |
| Offsets within the block | `uint16` |
| Ticks one hold covers | 1–64 (`MAX_HOLD_TICKS`) |
| Bytes one literal covers | 1–64 (`MAX_LITERAL_BYTES`) |
| Ticks one phrase token covers | 1–256 (`MAX_PHRASE_TICKS`) |
| Values one phrase holds | up to 255 (`MAX_PHRASE_LENGTH`) |
| Phrases one dictionary holds | up to 255 (`MAX_PHRASE_IDS`) |

A song that reaches past the space behind the driver, or past what an offset field can hold, raises
`SongTooLargeError` naming the part that overflowed. A project that offers more phrases than a dictionary
holds keeps the ones that spare the streams most, and says so.
