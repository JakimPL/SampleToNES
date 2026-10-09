# Song compression

This document explains the ideas behind fitting a whole song into the space an NES program has for it.
Read it before changing the encoder's scheme, or when you need to know what a layer earns. The layout
the encoder writes is in [NSF export](../formats/nsf.md). The package that implements it, with the driver that reads it back, is described in
[the console player](../development/player.md).

The other exports _SampleToNES_ writes describe a song to a program that already knows how to play one. An
`.nsf` carries its own player, so the song and the code that reads it share one 32 KB program area. Every
byte the song takes is a byte of cartridge space. Compression is part of the format.

The scheme works in layers, and each layer can be switched off on its own so that what it saves can be
measured ([section 6](#6-what-it-achieves)). Nothing here is lossy: the values the console writes to its
sound registers are exactly the values the sequencer plays.

## 1. The problem

A song reaches the console as **ticks**: the fixed-rate slices a reconstruction's envelopes advance
through, the same slices the sequencer sounds a row in. On every tick each of the four
[channels](../glossary.md#channel) has a full set of register values. Written out plainly, that is 11
bytes a tick: three each for the two pulse channels and the triangle, two for the noise.

At 60 ticks a second, 11 bytes a tick fills the space behind the driver in **48 seconds**. A song of three
minutes needs 118800 bytes, and the console has about 32000. So either songs stay under a minute, or the
stream is stored in a form the driver can unpack as it plays.

The content in those bytes is far smaller than the bytes themselves. What a tick says is a volume, a duty
cycle, a pitch and a noise period, roughly five bytes' worth even before anything repeats. And a great
deal repeats. A channel resting through a passage writes the same three bytes over and over. A song built
by playing the same drum sample at many rows writes that sample's envelopes once per row.

## 2. What a song looks like from the inside

### 2.1 Planes

The eleven bytes of a tick are stored channel by channel, so a channel's volume, its pitch low byte and
its pitch high byte sit next to each other. That adjacency hides the repetition: three unrelated series
interleaved turn over at every tick even when each of them is nearly constant.

The first thing the encoder does is separate them. Each register becomes a **plane**: one byte per tick,
the whole song long. Each plane is a series of its own: a volume envelope that falls and holds, a pitch
line that steps between notes, a duty cycle that barely moves. An idle channel's planes become one value
repeated, which costs almost nothing to state. A plane standing at the value it is seeded to throughout is
left out of the block altogether, such as a bend a channel never makes or the control byte of a channel
that never sounds.

This one change is most of the win. Split into planes and coded, the three-minute arrangement of
[section 6](#6-what-it-achieves) falls from 11 bytes a tick to 3.5.

### 2.2 Pitches instead of dividers

A tone channel names a pitch by the [divider](../glossary.md#divider) the hardware counts down from. The
divider takes two bytes and runs the opposite way to the note: higher notes have smaller dividers, and the
steps between them are uneven.

The encoder replaces the two divider planes with two other things. The **pitch index** is how far the
frame's note sits above the lowest pitch the table covers. The **bend** is the divider steps the tick
stands away from that note's own divider. The song block carries a table the driver resolves the index
through, and the driver adds the bend to the result. A pulse channel is therefore three planes. The
triangle is two: it sounds at one level, so its value plane carries the pitch and names silence with an
index no pitch uses. A bend is counted from the note, so it keeps the same bytes wherever a row transposes
the note to. Only a bend past the signed byte is counted from the pitch lying nearest the divider.

The bend plane has a value only where a note bends. The value plane's top bit flags each bent note from
its first bent tick to its last. The bend plane holds those ticks' steps alone, so it runs on a clock of
its own. A note played straight costs it nothing, and a channel that never bends leaves it out of the
block. A loop re-enters it at the value its flags have reached, which is a boundary like any other.

The saving of the planes comes from the triangle, whose value plane names silence, so its control byte
leaves the block. What the index earns is that **a pitch index can be
transposed and a divider cannot.** The same figure played at five pitches is five unrelated byte
sequences in divider space. In index space it is one sequence and five offsets, and its bend is the same
bytes throughout. That turns a repeated sample into a single dictionary entry
([section 5](#5-the-dictionary)).

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

Each plane is written as a sequence of **tokens**, and the driver reads them forward as the song plays. A
token says one of three things, and the opcode byte's top two bits say which:

- **Hold** keeps the value the plane reached, for up to `MAX_HOLD_TICKS` symbols. It takes one byte.
- **Literal** takes the next few bytes, one symbol each, up to `MAX_LITERAL_BYTES` of them. It takes one
  byte plus the values.
- **Phrase** plays entry *p* of the dictionary, for up to `MAX_PHRASE_TICKS` symbols, optionally with
  every value shifted. It takes one byte where it plays the count the phrase states, and a count byte more
  where it states its own. A full id byte and a shift add a byte each.

Literals alone can write any plane, so the codec always has an answer. Holds and phrases make that answer
short.

Three properties of the encoding do most of the work later.

**A token's count is a duration, not a length.** A phrase token says how many *symbols* it covers, and
that may run past the phrase's last value. Past the end, the plane holds that value onward. A note does
the same when its envelope has finished and the note is still sounding. One dictionary entry therefore
serves the same figure however long it is held. A count shorter than the body cuts the note off, as a
tracker does when the next note arrives early. So one entry covers every length a figure is played at.

**A shift is added within the byte.** A transposed phrase carries one byte that is added to each of its
values, wrapping at 256. On the 6502 that is a single addition, and a fall in pitch is the byte that wraps
around to it. Together with the duration rule, one entry covers every pitch *and* every length a figure is
played at.

**A phrase may state its own count.** A figure played at one length throughout states that length once, in
the phrase's own entry, and every token playing it there names the phrase alone. The bit that says so
comes out of the opcode's id field, so a phrase opcode names 31 ids outright where a hold counts to 64.
The phrases a song leans on hardest take those ids, and the rest name themselves in a further byte.

## 4. Reading a plane the cheapest way

A plane usually admits many readings. A run of eight identical values can be one hold, or two holds, or a
literal, or the tail of a phrase somebody else pays for. The readings cost different numbers of bytes, and
the differences compound over a song of thousands of ticks.

The encoder therefore searches for the cheapest reading. The plane becomes a graph. Each symbol is a node.
Each token that could start there is an edge to the symbol after the ones it covers, and the edge's weight
is the bytes that token takes. **The cheapest path across the plane is its encoding.** The weights are
bytes, so the search optimizes the quantity that has to fit in the program area.

### 4.1 The edges

From each symbol, the encoder offers:

- a **hold**, where the value repeats the one before it. It runs as far as the repeated run does, up to
  `MAX_HOLD_TICKS` symbols.
- a **literal**, reaching this symbol from the cheapest start within the last `MAX_LITERAL_BYTES` symbols.
- a **phrase**, one edge per dictionary entry the plane plays from here. It covers as many symbols as the
  plane agrees with the entry, plus however long the entry's last value carries.

A literal can start at any of the last `MAX_LITERAL_BYTES` symbols, and checking every start would make
the parse quadratic. A literal costs its opcode plus its bytes, whatever its length, so a start that a
later start beats stays beaten. The encoder keeps the live starts in order with the best at the front, and
it prices all of a plane's literals in one pass.

### 4.2 Why the search beats taking the longest match

The obvious alternative takes the longest phrase that matches at each symbol, otherwise a hold, otherwise
a literal. It goes wrong constantly. Taking a 40-symbol phrase for two bytes looks better than taking a
30-symbol one, until stopping at 30 would have let the next 60 symbols be a single hold. Costs also
depend on the dictionary: the same phrase is two bytes with a cheap id and four with an escaped id and a
shift. The search weighs those against each other, and a rule of thumb cannot.

### 4.3 Where a song comes round

A song that repeats re-enters its streams partway through and not at the beginning. The driver arrives
there with nothing behind it. It points each plane at a byte the header names and starts reading. For
that to work, the loop tick has to **begin** a symbol, and a token, on every plane, and that token has to
state its values outright instead of leaning on a value the plane reached earlier.

The parse takes this as a constraint. The loop tick is a boundary: tokens may end there and start there,
and none may span it. A hold cannot start there, because a hold leans on what came before. Literals and
phrases both state their own values, so either can open the loop.

## 5. The dictionary

The third token kind needs something to name. The dictionary is a table of **phrases**: runs of values a
plane plays. Each phrase is stored once in the song block and named by tokens wherever it occurs.

A phrase's position in the table is its id, and the ids are not equally priced. The ids below the escape
value fit inside the opcode byte, and the rest need a byte of their own. The order of the table is
therefore part of the encoding, and the phrases a song relies on most belong at the front.

### 5.1 The instruments seed it

A song is built by placing samples at rows, so the shapes its planes repeat are **knowable in advance and
need no discovery**. Each sample slice offers the two planes it writes, at the pitch and level it was
reconstructed at. Every row playing that sample becomes a token naming those entries with the shift the
row asks for. No search is involved. Most of a project's compression comes from here: on the arrangement
of [section 6](#6-what-it-achieves), the instruments alone take it from 2.980 bytes a tick to 1.717, and
transposition to 1.447.

A project can offer more phrases than the table holds, up to `MAX_PHRASE_IDS`. When it does, each phrase
is weighed by what it would spare the song, and the ones that pay most keep their place. The export says
so in the log, instead of dropping whichever sample happened to be listed last.

### 5.2 The search fills the rest

The instruments cover the notes and leave everything else: rests, tails, the transitions between rows, and
the whole of a reconstruction export, where each slice is played exactly once and nothing repeats by
construction.

The search works over that residue, the spans the current parse still spells out as literals. It gathers
every run of `MIN_CANDIDATE_LENGTH` to `MAX_CANDIDATE_LENGTH` symbols that appears in them. It groups the
runs by **shape**: the step from each value to the next. A figure played at five pitches then collects
into one candidate seen five times. Candidates occurring at least twice, in places that do not overlap,
are scored:

```
gain = what the current parse pays for those spans today
     − what tokens naming the phrase would pay instead
     − the entry the phrase takes in the dictionary
```

Scoring against **the current parse** and not against raw length keeps the search honest. A run of 40
identical values looks large by length and is worth nothing, because a hold already covers it for one
byte. Only spans the parse is paying for can pay a candidate back.

The best few candidates of each round are then confirmed the expensive way. The whole song is parsed again
with each one added, and the round keeps whichever shrank the total. The estimate ranks, and the re-parse
decides. Rounds continue until a round earns nothing.

### 5.3 Every entry pays for itself

An entry costs its table slot, its length byte and its values, whether or not anything names it. Being
used is not the same as being worth keeping. After the search, each phrase is weighed against a reading of
the song in which no phrase exists at all, and the phrases sparing fewer bytes than their entry takes are
dropped.

Dropping them changes which ids are cheap, which changes the parse, which changes what each phrase is
worth. The table is therefore rebuilt with the busiest phrases first and the song is parsed again. The
process repeats until it settles, for at most `SETTLING_ROUNDS` rounds.

## 6. What it achieves

Measured by `uv run sampletones codec report` over its three-minute arrangement of 10800 ticks, counting
the dictionary, the streams and the pitch table. Each row builds on the one above it:

| what is stored | bytes per tick | ratio | ticks that fit |
|---|---|---|---|
| a record per tick per channel | 11.000 | 1.00 | 2907 |
| a plane per register, in holds and literals | 3.517 | 3.13 | 9092 |
| planes with a pitch index and a bend, repeats packed | 2.980 | 3.69 | 10731 |
| phrases from the instruments | 1.717 | 6.41 | 18750 |
| phrases played transposed | 1.447 | 7.60 | 22326 |
| phrases from the search as well | **0.874** | **12.59** | **37660** |

The arrangement bends every note its first pulse channel plays, and that channel's bend plane carries
every one of them. A song played straight leaves its bend planes out of the block. The full scheme stores **37660 ticks, 10.5
minutes at 60 Hz**, in the space where a record per tick reaches 48 seconds. Encoding happens once, where
the file is written.

The format's constants are settled from a corpus of songs. The duty cycle stays in the control byte
because volume and duty turn over together, so a plane of its own pays two opcodes for what one covers
and gives up the repeat count its register's spare bits carry. The pitch index earns its place through
the transposition it makes possible, the fourth row of the table against the fifth.

An export chooses how far down these layers it goes. Its **Level** names the layers read in order:

- *None* spells every plane out as literals.
- *Held sounds* adds holds.
- *Samples* adds the phrases the project's samples seed, played transposed.
- *Full search* is the whole codec.

A lighter level finishes sooner and takes more room. Every level plays the same song.

## 7. Limitations

- **The search reads a dense plane only so far.** A reconstruction whose planes turn over at nearly every
  tick offers enormous numbers of candidates. A round gathers a fixed number of them, shared among the
  planes by what each has to offer. A plane that spells out little is read whole. A dense one is read as
  far as its share reaches, and the figures beyond that point go unsearched. It shows at lengths where the
  song already exceeds the program area, so it costs a diagnosis and not a song. A dense export of two
  minutes is stored materially larger than the same song at one.
- **The dictionary holds at most `MAX_PHRASE_IDS` phrases.** A project with enough samples fills it from
  its instruments alone. The search then has no room left to work in, and further samples compete for
  slots on measured value.
- **A phrase holds at most `MAX_PHRASE_LENGTH` values and a token covers at most `MAX_PHRASE_TICKS`
  symbols.** Longer figures are stated as several tokens, which costs a couple of bytes each time.
- **Compression is per plane.** Two channels playing the same figure at once share dictionary entries.
  Nothing exploits the correlation between a channel's own control and value planes.

## Appendix — where the exact shape is written

This page explains the scheme. The bytes themselves, with the opcodes, the operand each carries and the
bounds they impose, are in [NSF export](../formats/nsf.md).
