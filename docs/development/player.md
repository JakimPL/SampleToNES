# The console player

This document governs `sampletones_player`: the 6502 driver an exported `.nsf` carries, the
codec that fits a song into the console's program area, and the chain that holds both to
what the application plays. Read it before changing the assembly under
`driver/assembly/`, anything under `compression/`, or the way a song is built in
`builder.py`. The byte layout the two sides meet on is [the NSF format](../formats/nsf.md);
where the package sits among the others is [package layers](packages.md).

Everything else _SampleToNES_ exports describes a song to a program that plays it. This one
**is** the program. That single difference sets the whole design: the file has to carry a
player, the player has to fit beside the song in 32 KB, and the song has to be decodable by
a processor that has no multiply.

## Principles

**The driver interprets nothing.** Which value silences a channel, how a duty cycle reaches
its bits, how a pitch becomes a period, how the linear counter is held — every one of those
is settled in Python, under `registers/`, where it is testable at a keystroke. What crosses
into assembly is moving bytes to addresses and counting ticks. A rule that would have to be
debugged on a 6502 is a rule in the wrong place.

**What a correct driver writes is stated in Python, and the assembly is held to it.**
`RegisterTrace.from_song` says which APU registers a run touches, in what order, call by
call. The assembled driver is run on a 6502 emulator and its writes are compared against
that statement. The oracle is the contract; the assembly is an implementation of it, and
either one being wrong shows up as a difference rather than as a wrong sound.

**A song is decoded forward, never indexed.** Reading a tick by multiplying its number
bought exactly two things: skipping several ticks in one play call, and jumping to the loop
point. The first is a matter of decoding several ticks in a row; the second the header can
state outright. Giving both up in exchange for compression is what turns a program area
that holds seconds into one that holds minutes.

**The dictionary is the instrument table.** A song is built by playing samples at rows, so
the shapes its planes repeat are knowable rather than discoverable: each sample offers the
planes it writes, and every row playing it becomes a token naming that entry. Search fills
what the samples leave uncovered.

**Every layer earns its place on measured ground.** Each stage of the codec can be switched
off on its own, and `make compression-report` writes what each one saves across a corpus of
songs. The format's constants are settled from that report rather than from argument.

## The song a file carries

`Song` is the compressed song: the dictionary, the eight token streams, the timer table,
the clock and the loop point. The register values every channel writes are read back out of
the streams on demand, so a trace, a writer and a test all speak to the compressed song
without knowing it is one.

A song is built three ways, and the difference between them is only where the ticks come
from: `song_from_reconstruction` sounds a reconstruction's own instructions,
`song_from_sample` sounds the slices of an export request, and `song_from_project` plays a
whole arrangement out row by row through the same walk the sequencer sounds a song with.
The last of those is the one that seeds the dictionary from the project's samples.

A project carries no tuning of its own — each sample was reconstructed against one — so the
samples state it by agreeing on it, and a project whose samples disagree is refused rather
than sounded half in tune.

## The codec

The codec turns the four channels' per-tick register values into the eight token streams the
driver reads, and back again. `compression/decode.py` is the golden model: every encoding is
held against it, so what the console plays and what the encoder meant are the same values.

**Planes.** A channel's registers for one tick sit adjacent, which is exactly the
interleaving that destroys self-similarity — a volume envelope, a pitch line and a timbre
are unrelated series braided together. Split apart, each is a slowly-changing series of its
own.

**A pitch index rather than a timer.** A tone channel's two timer bytes become one index
into a table the block carries. It saves a byte a tick directly, but the reason it matters
is that a timer cannot be transposed and an index can: the same figure played at several
pitches is several copies in timer space and one entry plus a shift in index space.

**Tokens.** A plane is written as holds, literals and phrase plays — the encoding is in
[the format document](../formats/nsf.md#b4-the-token-streams). What matters here is that a
token's count is a duration rather than a length, so one dictionary entry serves a figure
however long it is held and whatever pitch it is played at.

**The cheapest reading, not a greedy one.** A plane is parsed as a shortest path: every way
of covering a tick is an edge priced in the bytes its token takes, and the cheapest path
across the plane is its encoding. Costs are in the currency the program area is measured in,
so the parse optimises the thing that actually has to fit.

**A phrase earns its entry.** Naming a phrase is not enough — an entry costs its own bytes.
Each is weighed by what it spares the streams against a reading of the song that names no
phrase at all, and the ones that fail to pay are dropped. Dropping them changes which ids
are cheap, so the table settles over a few rounds.

**Matching is measured once.** What a phrase plays against a plane at a position follows
from the plane and the phrase alone, so it holds for every parse the encoder runs. Measuring
it once per phrase, rather than once per parse, is what keeps the encoder's cost proportional
to the dictionary rather than to the dictionary times the parses.

A run reports what it holds as it goes and answers a caller that no longer wants it, in its
own vocabulary; the export backend translates that into the stages a user sees. The walk
through a project's song does the same, and it knows its length in advance, so it reads as a
true fraction of the song.

## The driver

The driver is three sources: the entry points and the play call in `driver.s`, the clock in
`clock.s`, and the eight plane decoders in `channels.s`.

**The clock steps a tick at a time.** A play call adds the header's step to an accumulator
and reads the whole ticks off the top; the driver then moves the clock on by one tick at a
time, and each step answers what the channels are to do with it — play it, play it from the
loop entry, or leave the console alone because the song has ended. Nothing wraps
arithmetically: reaching the end either points the planes at where the song comes round or
finishes.

**One routine plays a tick on every plane.** A plane's state carries where its next token
lies, where in a phrase body it stands, how much of that body is left, how much of the
current token is left, the value it last played, and the shift it is playing at. The three
kinds of token fold into that one shape — a hold is a phrase of no bytes, a literal is a
phrase whose bytes lie inline behind its opcode — so playing a tick is the same handful of
instructions whichever token is standing.

**The plane's own state block is the whole of the dispatch.** Which plane is being advanced
is a base offset held in `X`, the way a channel's register base is, so eight decoders are
one routine called eight times. The state lives in zero page, well inside what the driver
leaves free, and the linker configuration keeps the two-segment memory model an NSF loads.

## How it is verified

The chain runs from the register values upward, and each link is held on its own:

| Level | How |
|---|---|
| The codec is lossless | every encoding decodes to the planes it was written from, over a corpus |
| The codec is safe | a plane the codec finds nothing in stays within its literal bound |
| The ratio | `make compression-report` — bytes per tick and ticks that fit, per layer |
| The byte layout | a hand-built song serialises to expected bytes |
| The assembly agrees with the specification | the include's equates are read and compared field by field |
| The driver behaves | the assembled image on a 6502 emulator against `RegisterTrace.from_song`, over several rates and over songs that repeat |
| The audio | a captured trace re-rendered against the reconstruction's own approximation |
| The whole export | a project exported, played on the emulator, and read back as the instructions the sequencer sounds |
| Listening | `make nsf-samples` then `make nsf-render`, or any NSF player |
| Speed | `make benchmarks` — the encoder's own cost on the shapes that scale worst |

The audio comparison is the one that catches a mistake the trace would let through: the
trace says the right registers were written, and the render says the result is the waveform
the reconstruction was built as.

## Building the driver

`make player` assembles the sources with cc65 and writes `driver/binary/driver.bin`, which
is committed beside them — exporting an `.nsf` needs no assembler, and the wheel carries the
binary alone.

The link line names our own configuration and our own object files, with the CPU stated
outright. That is the guardrail that keeps the shipped image entirely ours: reaching for a
cc65 target or library would place that project's start-up code and runtime in the bytes the
package distributes. A build also holds the linker's own labels against the addresses the
exporter states without one, so the committed image and the header describing it cannot
drift apart.

Installing cc65 is covered in [dependencies](dependencies.md).
