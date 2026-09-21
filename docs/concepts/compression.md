# Song compression

This document explains how a whole song is squeezed into the space an NES program
has for it. It is written to be readable without the source code, and it covers
the ideas rather than the bytes: the layout the encoder writes is documented in
[NSF export](../formats/nsf.md), and the package that implements it, along with
the driver that reads it back, in [the console player](../development/player.md).

The other exports _SampleToNES_ writes describe a song to a program that already
knows how to play one. An `.nsf` carries its own player, so the song and the code
that reads it share one 32 KB program area, and every byte the song takes is a byte
the console has to hold in cartridge space. This is what makes compression part of
the format rather than a convenience on top of it.

The scheme is four layers, and each can be switched off on its own so that what it
saves can be measured (§6). Nothing here is lossy: the values the console writes to
its sound registers are exactly the values the sequencer plays.

## 1. The problem

A song reaches the console as **ticks** — the fixed-rate slices a reconstruction's
envelopes advance through, the same slices the sequencer sounds a row in. On every
tick each of the four [channels](../glossary.md#channel) has a full set of register
values, and written out plainly that is 11 bytes a tick: three each for the two pulse
channels and the triangle, two for the noise.

At 60 ticks a second, 11 bytes a tick fills the space behind the driver in **49
seconds**. A song of three minutes needs 118800 bytes and the console has about
32000. So either songs stay under a minute, or the stream is stored in a form the
driver can unpack as it plays.

The content in those bytes is far smaller than the bytes themselves. What a tick
actually says is a volume, a duty cycle, a pitch and a noise period — roughly four
bytes' worth even before anything repeats. And a great deal repeats: a channel
resting through a passage writes the same three bytes hundreds of times over, and a
song built by playing the same drum sample at forty rows writes that sample's
envelopes forty times.

## 2. What a song looks like from the inside

### 2.1 Planes

The eleven bytes of a tick are stored channel by channel, so a channel's volume, its
pitch low byte and its pitch high byte sit next to each other. That adjacency is
exactly what hides the repetition: three unrelated series braided together turn over
at every tick even when each of them is nearly constant.

The first thing the encoder does is unbraid them. Each register becomes a **plane** —
one byte per tick, the whole song long — and each plane is a series of its own: a
volume envelope that falls and holds, a pitch line that steps between notes, a duty
cycle that barely moves. An idle channel's planes become one value repeated, which
costs almost nothing to state, and a plane standing at the value it is seeded to throughout is left out
of the block altogether: a bend a channel never makes, the control byte of a channel that never sounds.

This one change is most of the win. Split into planes and coded, the three-minute arrangement falls from
11 bytes a tick to 3.5.

### 2.2 Pitches instead of dividers

A tone channel names a pitch by the **divider** the hardware counts down from, which
takes two bytes and runs the opposite way to the note: higher notes have smaller
dividers, and the steps between them are uneven. The encoder replaces the two
divider planes with a **pitch index** — how far the frame's note sits above the lowest
pitch the table covers — and a **bend**, the divider steps the tick stands away from that
note's own divider. The song block carries a table the driver resolves the index through
and adds the bend to. A pulse channel is therefore three planes. The triangle is two: it sounds at one
level, so its value plane carries the pitch and names silence with an index no pitch uses. Counting a bend
from the note keeps it the same bytes wherever a row transposes the note to. Only a bend past the signed
byte is counted from the pitch lying nearest the divider instead.

The bend plane holds a value only where a note bends. The value plane's top bit flags each
bent note from its first bent tick to its last, and the bend plane holds those ticks' steps
alone, so it runs on a clock of its own: a note played straight costs it nothing, and a
channel that never bends leaves it out of the block. A loop re-enters it at the value its
flags have reached, which is a boundary like any other.

Before any phrase, trading two dividers for an index and a bend already pays. On the arrangement §6
measures, which bends most of its notes, the planes take 3.210 bytes a tick against 3.517, because a bend
plane holds a value only where a note bends. What it earns beyond that is that **a pitch index can be
transposed and a divider cannot.** The same figure played
at five pitches is five unrelated byte sequences in divider space; in index space it
is one sequence and five offsets, its bend the same bytes throughout. That is what turns
a repeated sample into a single dictionary entry in §5.

### 2.3 A value and the ticks it lasts

A register rarely reads every bit of the byte written to it. A pulse control byte holds a duty cycle and a
volume around two bits the hardware wants set. A noise control byte holds a volume under the same two. A
noise period byte holds a mode bit above three the register reads nothing from. Those spare bits carry no
sound, and a long reconstruction spends most of its planes repeating one value.

So a plane states the value and the ticks it lasts in the same byte: the value in the bits the register
reads, the count in the bits it ignores. That byte is a **symbol**, and a run costs one byte however long
it lasts, up to the count the plane's own spare bits reach. The driver masks a symbol to the register byte
and ors in the bits the hardware fixes, and counting one repeat off is a subtraction.

A plane whose register reads all eight bits keeps a symbol a tick, so both kinds read the same way and the
block states no division of its own. **Every count in the token language counts symbols**, and a symbol
covers the ticks its own count states.

## 3. The token language

Each plane is written as a sequence of **tokens**, and the driver reads them forward as
the song plays. There are three things a token can say, and the opcode byte's top
two bits say which:

- **Hold** — keep the value the plane reached, for up to 64 symbols. One byte.
- **Literal** — take the next few bytes, one symbol each, up to 64 of them. One byte plus
  the values.
- **Phrase** — play entry *p* of the dictionary, for up to 256 symbols, optionally with
  every value shifted. Two bytes, three if the phrase needs a full id byte or a shift,
  four if it needs both.

Literals alone can write any plane, so the codec always has an answer; holds and
phrases are what make that answer short.

Three properties of the encoding do most of the work later:

**A token's count is a duration, not a length.** A phrase token says how many *symbols*
it covers, and that may run past the phrase's last value — past the end, the plane
holds that value onward. This is what a note does when its envelope has finished and
the note is still sounding, and it means one dictionary entry serves the same figure
however long it is held. A count shorter than the body cuts the note off, which is
what a tracker does when the next note arrives early. So one entry covers every length
a figure is played at.

**A shift is added within the byte.** A transposed phrase carries one byte that is
added to each of its values, wrapping at 256. On the 6502 that is a single addition,
and a fall in pitch is simply the byte that wraps around to it. Together with the
duration rule, one entry covers every pitch *and* every length a figure is played at.

**A phrase may state its own count.** A figure played at one length throughout states that length once, in
the phrase's own entry, and every token playing it there names the phrase alone. The bit that says so
comes out of the opcode's id field, so a phrase opcode names 31 ids outright where a hold counts to 64.
The phrases a song leans on hardest take those ids, and the rest name themselves in a further byte.

## 4. Reading a plane the cheapest way

A plane usually admits many readings. A run of eight identical values can be one hold,
or two holds, or a literal, or the tail of a phrase somebody else pays for. The
readings cost different numbers of bytes, and the differences compound over a song of
thousands of ticks.

So the encoder does not pick a reading by rules of thumb; it searches for the cheapest
one. The plane becomes a graph: each symbol is a node, each token that could start there
is an edge to the symbol after the ones it covers, and the edge's weight is the bytes
that token takes. **The cheapest path across the plane is its encoding** — and because
the weights are bytes, the search optimizes the very quantity that has to fit in the
program area.

### 4.1 The edges

From each symbol, the encoder offers:

- a **hold**, where the value repeats the one before it, running as far as the repeated
  run does, capped at 64 symbols;
- a **literal**, reaching this symbol from the cheapest start within the last 64 symbols;
- a **phrase**, one edge per dictionary entry the plane plays from here, covering as
  many symbols as the plane agrees with it plus however long its last value carries.

Literals need care, because every one of the 64 possible starts is a candidate and
checking them all would make the parse quadratic. A literal costs its opcode and its
bytes whatever its length, so a start that is beaten by a later one is beaten for good;
keeping the live starts in that order leaves the best of them at the front, and the
whole plane's literals are priced in one pass.

### 4.2 Why the search beats taking the longest match

The obvious alternative — at each symbol take the longest phrase that matches, otherwise
hold, otherwise spell out — is wrong in a way that shows up constantly. Taking a
40-symbol phrase for two bytes looks better than taking a 30-symbol one, until it turns out
that stopping at 30 would have let the next 200 symbols be a single hold. Costs also
depend on the dictionary: the same phrase is two bytes with a cheap id and four with an
escaped id and a shift. The search weighs those against each other; a rule of thumb
cannot.

### 4.3 Where a song comes round

A song that repeats re-enters its streams partway through rather than at the beginning,
and the driver arrives there with nothing behind it: it points each plane at a byte the
header names and starts reading. For that to work, the loop tick has to **begin** a
symbol, and a token, on every plane, and that token has to state its values outright rather
than lean on a value the plane reached earlier.

The parse takes this as a constraint. The loop tick is a boundary: tokens may end there
and start there, and none may span it. A hold is barred from starting there, since a
hold is precisely a token that leans on what came before. Literals and phrases both
state their own values, so either can open the loop.

## 5. The dictionary

The third token kind needs something to name. The dictionary is a table of **phrases** —
runs of values a plane plays — stored once in the song block and named by tokens
wherever they occur.

A phrase's position in the table is its id, and the ids are not equally priced: the
first 31 ride inside the opcode byte, and the rest need a byte of their own. So the
order of the table is part of the encoding, and the phrases a song leans on hardest
belong at the front.

### 5.1 The instruments seed it

A song is built by placing samples at rows, so the shapes its planes repeat are
**knowable in advance rather than discoverable**. Each sample slice offers the two
planes it writes, at the pitch and level it was reconstructed at, and every row playing
that sample becomes a token naming those entries with the shift the row asks for. No
search is involved, and this is where most of a project's compression comes from: on
the three-minute arrangement §6 measures, the instruments alone take it from 2.980 bytes
a tick to 1.717, and transposition to 1.447.

A project can offer more phrases than the table holds. When it does, each is weighed by
what it would actually spare the song, and the ones that pay most keep their place; the
export says so in the log rather than quietly dropping whichever sample happened to be
listed last.

### 5.2 The search fills the rest

The instruments cover the notes, and leave behind everything else: rests, tails, the
transitions between rows, and the whole of a reconstruction export, where each slice is
played exactly once and nothing repeats by construction.

The search works over that residue — the spans the current parse still spells out as
literals. It gathers every run of 3 to 48 symbols that appears in them and groups them by
**shape**: the step from each value to the next, so a figure played at five pitches
collects into one candidate seen five times. Candidates occurring at least twice, in
places that do not overlap, are scored:

```
gain = what the current parse pays for those spans today
     − what tokens naming the phrase would pay instead
     − the entry the phrase takes in the dictionary
```

Scoring against **the current parse** rather than against raw length is what keeps the
search honest. A run of 200 identical values looks enormous by length and is worth
nothing, because a hold already covers it for one byte. Only spans the parse is
genuinely paying for can pay a candidate back.

The best few candidates of each round are then confirmed the expensive way: the whole
song is parsed again with each one added, and the round keeps whichever actually
shrank the total. The estimate ranks; the re-parse decides. Rounds continue until a
round earns nothing.

### 5.3 Every entry pays for itself

An entry costs its table slot, its length byte and its values, whether or not anything
names it — so being used is not the same as being worth keeping. After the search, each
phrase is weighed against a reading of the song in which no phrase exists at all, and
the ones sparing fewer bytes than their entry takes are dropped.

Dropping them changes which ids are cheap, which changes the parse, which changes what
each phrase is worth. So the table is rebuilt with the busiest phrases first, the song
is parsed again, and the process repeats until it settles — a few rounds at most.

### 5.4 Matching is measured once

The encoder parses the whole song many times: once as a baseline, once per confirmed
candidate, once per settling round. A parse asks the same question at every symbol — what
does this phrase play here, and for how many symbols — and the answer depends only on the
plane and the phrase. It cannot change between parses.

So it is measured once per plane per phrase and kept for the whole encoding. A search
round that adds one phrase measures that one phrase; everything already in the table
answers from the reading taken when it arrived. This turns the cost of an encode from
*parses × dictionary* into *dictionary*, and it is the largest reason a three-minute
song encodes in about two seconds. Phrases are also offered only at the symbols whose
first two steps match their own, so a reading covers the handful of places a phrase
could begin rather than every symbol of the song.

## 6. What it achieves

Measured over a three-minute arrangement, 10800 ticks, each layer added to the ones
above it:

| what is stored | bytes per tick | ratio | ticks that fit |
|---|---|---|---|
| a record per tick per channel | 11.000 | 1.00 | 2907 |
| planes, coded | 3.517 | 3.13 | 9092 |
| planes with a pitch index and a bend | 2.980 | 3.69 | 10731 |
| phrases from the instruments | 1.717 | 6.41 | 18750 |
| phrases played transposed | 1.447 | 7.60 | 22326 |
| phrases from the search as well | **0.874** | **12.59** | **37660** |

The arrangement bends most of the notes its pulse channel plays, and its bend plane carries every one of
them. A song played straight leaves its bend planes out of the block. The whole song is 9435 bytes of the
roughly 32000 available, and **37660 ticks is 10.5 minutes at 60 Hz**, against the 49 seconds a record per
tick reaches. Encoding happens once, where the file is written. Decoding costs the console around twenty
instructions per plane per tick, and fewer on a tick a symbol still covers, comfortably inside a video
frame.

The report writes this table over a corpus of songs, and the format's constants are settled from it. Two
of them were settled against expectation. Splitting the duty cycle out of the control byte into a plane of
its own **costs** bytes: 16 % on the arrangement above with no plane packed at all, because volume and
duty turn over together and a split pays two opcodes for what one covers, and 56 % as the format stands,
because a split plane also gives up the repeat count its register's spare bits carry. The pitch index
earns its place through the transposition it makes possible, the fourth row against the fifth, and it pays
for itself directly as well (§2.2).

An export chooses how far down these layers it goes. The **Level** it is written at names the
layers read in order: *None* spells every plane out as literals, *Held sounds* adds holds,
*Samples* adds the phrases the project's samples seed, played transposed, and *Full search* is
the whole codec. A lighter level finishes sooner and takes more room, and every one of them
plays the same song.

## 7. Limitations

- **The search reads a dense plane only so far.** A reconstruction whose planes turn over
  at nearly every tick offers enormous numbers of candidates, and a round gathers a fixed
  number of them, shared among the planes by what each has to offer. A plane that spells out
  little is read whole; a dense one is read as far as its share reaches, and the figures
  beyond that point go unsearched. It bites at lengths where the song already exceeds the
  program area, so it costs a diagnosis rather than a song, but a dense export of two
  minutes is stored materially larger than the same song at one.
- **The dictionary holds 255 phrases.** A project of roughly 30 to 60 samples fills it
  from its instruments alone, at which point the search has no room left to work in and
  further samples compete for slots on measured value.
- **A phrase holds at most 255 values and a token covers at most 256 symbols.** Longer
  figures are stated as several tokens, which costs a couple of bytes each time.
- **Compression is per plane.** Two channels playing the same figure at once share
  dictionary entries, and nothing exploits the correlation between a channel's own
  control and value planes.

## Appendix — where the exact shape is written

This page explains the scheme. The bytes themselves — the opcodes, the operand each carries and
the bounds they impose — are in [NSF export](../formats/nsf.md).
