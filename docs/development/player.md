# The console player

This document governs `sampletones_player`: the 6502 driver an exported `.nsf` carries, the codec that fits a
song into the console's program area, and the chain that holds both to what the application plays. Read it
before changing the assembly under `sampletones_tools/player/assembly/`, anything under `compression/`, or
the way a song is built in `builder.py`. The byte layout the two sides meet on is
[the NSF format](../formats/nsf.md). [Package layers](packages.md) says where the package sits among the
others.

Everything else _SampleToNES_ exports describes a song to a program that plays it. This one **is** the
program. That single difference sets the whole design. The file has to carry a player, the player has to
fit beside the song in 32 KB, and the song has to be decodable by a processor with no multiply.

## Principles

**Python settles every rule, and the driver moves bytes.** Which value silences a channel, how a duty cycle
reaches its bits, how a pitch becomes a period, how the linear counter is held: each of these is settled
in Python, under `registers/`, where it is testable at a keystroke. What crosses into assembly is moving
bytes to addresses and counting ticks. A rule that would have to be debugged on a 6502 is a rule in the
wrong place.

**What a correct driver writes is stated in Python, and the assembly is held to it.**
`RegisterTrace.from_song` says which APU registers a run touches, in what order, call by call. The
assembled driver runs on a 6502 emulator, and its writes are compared against that statement. The oracle
is the contract, and the assembly is an implementation of it. A fault in either one shows up as a
difference and not as a wrong sound.

**A song is decoded forward.** Reading a tick by multiplying its number would allow two things: skipping
several ticks in one play call, and jumping to the loop point. Decoding several ticks in a row covers the
first, and the header can state the second outright. Giving up indexing is what turns a program area that
holds seconds into one that holds minutes.

**The dictionary is the instrument table.** A song is built by playing samples at rows, so the shapes its
planes repeat are knowable in advance. Each sample offers the planes it writes, and every row playing it
becomes a token naming that entry. Search fills what the samples leave uncovered.

**Every layer earns its place on measured ground.** Each stage of the codec can be switched off on its
own, and `uv run sampletones codec report` writes what each one saves across a corpus of songs. The
format's constants are settled from that report and not from argument.

**A change to the codec is measured before it is built.** `uv run sampletones codec study` reads the
projects and stems named on its command line, encodes every song under every candidate change, and writes
the sizes, the times, a verdict per candidate and the manifest that repeats the run under
`Documents/SampleToNES/compression`. A candidate is one of two things. A new way of choosing tokens is
encoded and played back by the production codec itself. A new token grammar is priced in bytes by a study
parser, which first has to reproduce the production parser's bytes on today's grammar. The report prints
the rule that gives a candidate a production layer: it must save a set share of the projects' or of the
reconstructions' bytes, and it must not grow any song beyond a set margin. The study lives under
`sampletones_tools/codec/study`, outside the shipped packages.

## The song a file carries

`Song` is the compressed song: the dictionary, one token stream per plane, the timer table, the clock and
the loop point. The register values every channel writes are read back out of the streams on demand, so a
trace, a writer and a test all speak to the compressed song without knowing it is one.

A song is built from a reconstruction's own instructions, from the slices of an export request, or from a
whole project. The three differ only in where the ticks come from. A project is played out row by row
through the same walk the sequencer sounds a song with, and it is the case that seeds the dictionary from
the project's samples.

**A program states what an export chooses.** `NSFProgram` holds the channels a song sounds, the tick it
returns to, the `CompressionScheme` it is written with and the header text. The builders take the first
three explicitly. The defaults an export writes when nobody chose otherwise are stated once, and the export
dialog opens on the same values. A user's choice replaces those defaults, so the service that runs an
export stays free of anything the format decides.

A project has no tuning of its own, because each sample was reconstructed against one. The samples
therefore state the tuning by agreeing on it. A project whose samples disagree is refused, so nothing
sounds half in tune.

## The codec

The codec turns the four channels' per-tick register values into the token streams the
driver reads, and back again. `compression/decode.py` is the golden model: every encoding is
held against it, so what the console plays and what the encoder meant are the same values.
The scheme itself, with the measurements each layer is settled on, is
[song compression](../concepts/compression.md); what governs it here is where each part
belongs and what holds it.

**Planes.** A channel's registers for one tick sit adjacent, which is exactly the
interleaving that destroys self-similarity — a volume envelope, a pitch line and a timbre
are unrelated series braided together. Split apart, each is a slowly-changing series of its
own.

**A pitch index rather than a timer.** A tone channel's two timer bytes become one index
into a table the block carries, beside a bend holding the steps a bent tick stands away
from that pitch. It saves a byte a tick directly, but the reason it matters is that a timer
cannot be transposed and an index can: the same figure played at several pitches is several
copies in timer space and one entry plus a shift in index space.

**A plane repeats from its own byte.** Four of the planes write a byte the APU only
partly reads — two bits a pulse control byte wants set, the top nibble of a noise control
byte, three bits above a noise period — and those spare bits carry the ticks the value
repeats for. A rest costs one byte however long it lasts, and the planes that rest longest
are exactly the ones with room to say so. The division follows from the register, so the
block states none of it and the driver knows it by plane.

**The triangle names its silence in the pitch it plays.** The channel sounds at one level,
so the index its value plane carries is enough to say whether it sounds at all: an index
above every pitch the table holds silences the linear counter. That spares a whole plane,
in the block and on the tick path both.

**Tokens.** A plane is written as holds, literals and phrase plays — the encoding is in
[the format document](../formats/nsf.md#b4-the-token-streams). What matters here is that a
token's count is a duration rather than a length, so one dictionary entry serves a figure
however long it is held and whatever pitch it is played at, and that a phrase may state
the count its tokens play it at most often so those tokens carry none.

**The cheapest reading, not a greedy one.** A plane is parsed as a shortest path: every way
of covering a tick is an edge priced in the bytes its token takes, and the cheapest path
across the plane is its encoding. Costs are in the currency the program area is measured in,
so the parse optimizes the thing that actually has to fit.

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

**The clock steps a tick at a time.** A play call adds the header's step to an accumulator
and reads the whole ticks off the top; the driver then moves the clock on by one tick at a
time, and each step answers what the channels are to do with it — play it, play it from the
loop entry, or leave the console alone because the song has ended. Nothing wraps
arithmetically: reaching the end either points the planes at where the song comes round or
finishes.

**One routine plays a tick on every plane the block holds.** An absent plane's source is
seeded into page zero, which no song occupies, and the advance passes it by, so it stands at
the zero every plane starts from. A bend plane is stepped only on a tick its channel's new
value flags, since it holds a value for those ticks alone. A plane's state carries where its next token
lies, where in a phrase body it stands, how much of that body is left, how much of the
current token is left, the symbol it last played, the ticks that symbol still covers, the
bits its own byte counts in, and the shift it is playing at. The three
kinds of token fold into that one shape — a hold is a phrase of no bytes, a literal is a
phrase whose bytes lie inline behind its opcode — so playing a tick is the same handful of
instructions whichever token is standing.

**The plane's own state block is the whole of the dispatch.** Which plane is being advanced
is a base offset held in `X`, the way a channel's register base is, so every plane's decoder
is one routine called again. The state lives in zero page, well inside what the driver
leaves free, and the linker configuration keeps the two-segment memory model an NSF loads.

**The driver's arithmetic is the bend and the repeat.** A tone channel's value plane
resolves to a divider through the timer table, and on a flagged tick its bend plane states
the steps the tick stands away from it — sign-extended and added across both halves of the
timer, with the high half reaching the register only where it changed. An unflagged tick
adds nothing. The other is a subtraction: a tick a symbol still covers steps the plane's
count down and returns, which makes the common tick cheaper than reaching a new symbol.
Everything that keeps either in range is settled in Python, so what crosses into assembly
stays a byte moved and a carry followed.

## How it is verified

The chain runs from the register values upward, and each link is held on its own: the codec against its
golden decoder over a corpus, the byte layout against a hand-built song, the assembly's equates against
`specification/`, and the assembled image on a 6502 emulator against `RegisterTrace.from_song`. On top sits
a whole export: a project exported, played on the emulator, and read back as the instructions the sequencer
sounds.

One more check covers what the others cannot. The trace says the right registers were written. The audio
comparison re-renders a captured trace against the reconstruction's own approximation and says the result
is the waveform the reconstruction was built as.

## Building the driver

The driver binary is committed as `sampletones_player/driver/binary/driver.bin`, so exporting an
`.nsf` needs no assembler and the application ships the binary alone. `uv run sampletones driver`
rebuilds it from the sources under `sampletones_tools/player/assembly/` and prints the layout the
build produced.

The link line names this project's own configuration and object files and states the CPU outright. That
keeps the shipped image entirely ours: a cc65 target or library would place that project's start-up code
and runtime in the bytes the package distributes. A build also holds the linker's own labels against the
addresses the exporter states without one, so the committed image and the header describing it stay in
step.

Installing cc65 is covered in [dependencies](release/dependencies.md).
