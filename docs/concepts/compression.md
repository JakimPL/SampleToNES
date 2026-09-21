# Song compression

This document explains the ideas behind fitting a whole song into the space an NES program has for it.
Read it before changing the encoder's scheme, or when you need to know what a layer earns. You can read it
without the source code. The layout the encoder writes is in [NSF export](../formats/nsf.md). The package
that implements it, with the driver that reads it back, is described in
[the console player](../development/player.md).

The other exports _SampleToNES_ writes describe a song to a program that already knows how to play one. An
`.nsf` carries its own player, so the song and the code that reads it share one 32 KB program area. Every
byte the song takes is a byte of cartridge space. Compression is therefore part of the format and not a
convenience on top of it.

The scheme works in layers, and each layer can be switched off on its own so that what it saves can be
measured ([section 6](#6-what-it-achieves)). Nothing here is lossy: the values the console writes to its
sound registers are exactly the values the sequencer plays.

## 1. The problem

A song reaches the console as **ticks**: the fixed-rate slices a reconstruction's envelopes advance
through, the same slices the sequencer sounds a row in. On every tick each of the four
[channels](../glossary.md#channel) has a full set of register values. Written out plainly, that is 11
bytes a tick: three each for the two pulse channels and the triangle, two for the noise.

At 60 ticks a second, 11 bytes a tick fills the space behind the driver in **49 seconds**. A song of three
minutes needs 118800 bytes, and the console has about 32000. So either songs stay under a minute, or the
stream is stored in a form the driver can unpack as it plays.

The content in those bytes is far smaller than the bytes themselves. What a tick says is a volume, a duty
cycle, a pitch and a noise period, roughly four bytes' worth even before anything repeats. And a great
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
repeated, which costs almost nothing to state. A plane holding zero throughout, such as a bend a channel
never makes, is left out of the block altogether.

This one change is most of the win. Split into planes and coded, the three-minute arrangement of
[section 6](#6-what-it-achieves) falls to about a third of its size.

### 2.2 Pitches instead of dividers

A tone channel names a pitch by the [divider](../glossary.md#divider) the hardware counts down from. The
divider takes two bytes and runs the opposite way to the note: higher notes have smaller dividers, and the
steps between them are uneven.

The encoder replaces the two divider planes with two other things. The **pitch index** is how far the
frame's note sits above the lowest pitch the table covers. The **bend** is the divider steps the tick
stands away from that note's own divider. The song block carries a table the driver resolves the index
through, and the driver adds the bend to the result. A tone channel is therefore three planes, the same
count as the registers it writes. A bend is counted from the note, so it keeps the same bytes wherever a
row transposes the note to. Only a bend past the signed byte is counted from the pitch lying nearest the
divider.

The bend plane has a value only where a note bends. The value plane's top bit flags each bent note from
its first bent tick to its last. The bend plane holds those ticks' steps alone, so it runs on a clock of
its own. A note played straight costs it nothing, and a channel that never bends leaves it out of the
block. A loop re-enters it at the value its flags have reached, which is a boundary like any other.

Before any phrase, trading two dividers for an index and a bend gains little. On the arrangement of
[section 6](#6-what-it-achieves), which bends most of its notes, it costs a few percent. What it earns is
that **a pitch index can be transposed and a divider cannot.** The same figure played at five pitches is
five unrelated byte sequences in divider space. In index space it is one sequence and five offsets, and
its bend is the same bytes throughout. That turns a repeated sample into a single dictionary entry
([section 5](#5-the-dictionary)).

## 3. The token language

Each plane is written as a sequence of **tokens**, and the driver reads them forward, one tick at a time.
A token says one of three things, and the opcode byte's top two bits say which:

- **Hold** keeps the value the plane reached, for up to `MAX_HOLD_TICKS` ticks. It takes one byte.
- **Literal** takes the next few bytes, one per tick, up to `MAX_LITERAL_BYTES` of them. It takes one byte
  plus the values.
- **Phrase** plays entry *p* of the dictionary, for up to `MAX_PHRASE_TICKS` ticks, optionally with every
  value shifted. It takes two bytes. It takes three if the phrase needs a full id byte or a shift, and
  four if it needs both.

Literals alone can write any plane, so the codec always has an answer. Holds and phrases make that answer
short.

Two properties of the encoding do most of the work later.

**A token's count is a duration, not a length.** A phrase token says how many *ticks* it covers, and that
may run past the phrase's last value. Past the end, the plane holds that value onward. A note does the
same when its envelope has finished and the note is still sounding. One dictionary entry therefore serves
the same figure however long it is held. A count shorter than the body cuts the note off, as a tracker
does when the next note arrives early. So one entry covers every length a figure is played at.

**A shift is added within the byte.** A transposed phrase carries one byte that is added to each of its
values, wrapping at 256. On the 6502 that is a single addition, and a fall in pitch is the byte that wraps
around to it. Together with the duration rule, one entry covers every pitch *and* every length a figure is
played at.

## 4. Reading a plane the cheapest way

A plane usually admits many readings. A run of eight identical values can be one hold, or two holds, or a
literal, or the tail of a phrase somebody else pays for. The readings cost different numbers of bytes, and
the differences compound over a song of thousands of ticks.

The encoder therefore searches for the cheapest reading. The plane becomes a graph. Each tick is a node.
Each token that could start there is an edge to the tick after the ones it covers, and the edge's weight
is the bytes that token takes. **The cheapest path across the plane is its encoding.** The weights are
bytes, so the search optimizes the quantity that has to fit in the program area.

### 4.1 The edges

From each tick, the encoder offers:

- a **hold**, where the value repeats the one before it. It runs as far as the repeated run does, up to
  `MAX_HOLD_TICKS`.
- a **literal**, reaching this tick from the cheapest start within the last `MAX_LITERAL_BYTES` ticks.
- a **phrase**, one edge per dictionary entry the plane plays from here. It covers as many ticks as the
  plane agrees with the entry, plus however long the entry's last value carries.

A literal can start at any of the last `MAX_LITERAL_BYTES` ticks, and checking every start would make the
parse quadratic. A literal costs its opcode plus its bytes, whatever its length, so a start that a later
start beats stays beaten. The encoder keeps the live starts in order with the best at the front, and it
prices all of a plane's literals in one pass.

### 4.2 Why the search beats taking the longest match

The obvious alternative takes the longest phrase that matches at each tick, otherwise a hold, otherwise a
literal. It goes wrong constantly. Taking a 40-tick phrase for two bytes looks better than taking a
30-tick one, until stopping at 30 would have let the next 200 ticks be a single hold. Costs also depend on
the dictionary: the same phrase is two bytes with a cheap id and four with an escaped id and a shift. The
search weighs those against each other, and a rule of thumb cannot.

### 4.3 Where a song comes round

A song that repeats re-enters its streams partway through and not at the beginning. The driver arrives
there with nothing behind it. It points each plane at a byte the header names and starts reading. For
that to work, the loop tick has to **begin** a token on every plane, and that token has to state its
values outright instead of leaning on a value the plane reached earlier.

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
row asks for. No search is involved. Most of a project's compression comes from here: in the table of
[section 6](#6-what-it-achieves), the phrases from the instruments shrink the song the most, and playing
them transposed shrinks it further.

A project can offer more phrases than the table holds, up to `MAX_PHRASE_IDS`. When it does, each phrase
is weighed by what it would spare the song, and the ones that pay most keep their place. The export says
so in the log, instead of dropping whichever sample happened to be listed last.

### 5.2 The search fills the rest

The instruments cover the notes and leave everything else: rests, tails, the transitions between rows, and
the whole of a reconstruction export, where each slice is played exactly once and nothing repeats by
construction.

The search works over that residue, the spans the current parse still spells out as literals. It gathers
every run of `MIN_CANDIDATE_LENGTH` to `MAX_CANDIDATE_LENGTH` ticks that appears in them. It groups the
runs by **shape**: the step from each value to the next. A figure played at five pitches then collects
into one candidate seen five times. Candidates occurring at least twice, in places that do not overlap,
are scored:

```
gain = what the current parse pays for those spans today
     − what tokens naming the phrase would pay instead
     − the entry the phrase takes in the dictionary
```

Scoring against **the current parse** and not against raw length keeps the search honest. A run of 200
identical values looks enormous by length and is worth nothing, because a hold already covers it for one
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

### 5.4 Matching is measured once

The encoder parses the whole song many times: once as a baseline, once per confirmed candidate and once
per settling round. Every parse asks the same question at every tick: what does this phrase play here, and
for how many ticks. The answer depends only on the plane and the phrase, so it is the same in every parse.

The encoder therefore measures it once per plane per phrase and keeps it for the whole encoding. A search
round that adds one phrase measures that one phrase, and everything already in the table answers from the
reading taken when it arrived. This turns the cost of an encode from *parses × dictionary* into
*dictionary*, which is the largest reason a long song encodes quickly. Phrases are also offered only at
the ticks whose first two steps match their own, so a reading covers the handful of places a phrase could
begin and not every tick of the song.

## 6. What it achieves

Measured over a three-minute arrangement of 10800 ticks, each layer added to the ones above it:

| what is stored | bytes per tick | ratio | ticks that fit |
|---|---|---|---|
| a record per tick per channel | 11.000 | 1.00 | 2914 |
| planes, coded | 3.517 | 3.13 | 9115 |
| planes with a pitch index and a bend | 3.604 | 3.05 | 8885 |
| phrases from the instruments | 1.989 | 5.53 | 16201 |
| phrases played transposed | 1.593 | 6.90 | 20294 |
| phrases from the search as well | **1.346** | **8.17** | **24130** |

The last row fits about 6.7 minutes at 60 Hz, against the 49 seconds a record per tick reaches. Encoding
happens once, where the file is written. Decoding costs the console a small, fixed amount of work per
plane per tick, well inside a video frame.

The format's constants are settled from a corpus of songs. Two results went against expectation.
Splitting the duty cycle out of the control byte into a plane of its own **raised** the size by 14 %,
because volume and duty turn over together, and a split pays two opcodes for what one covers. The pitch
index earns its place through the transposition it makes possible, 20 % in the table above, even though
by itself it costs the bent arrangement a few percent.

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
  ticks.** Longer figures are stated as several tokens, which costs a couple of bytes each time.
- **Compression is per plane.** Two channels playing the same figure at once share dictionary entries.
  Nothing exploits the correlation between a channel's own control and value planes.

## Appendix — where the exact shape is written

This page explains the scheme. The bytes themselves, with the opcodes, the operand each carries and the
bounds they impose, are in [NSF export](../formats/nsf.md).
