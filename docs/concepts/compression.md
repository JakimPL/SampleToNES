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
tick each of the four channels has a full set of register values, and written out
plainly that is 11 bytes a tick: three each for the two pulse channels and the
triangle, two for the noise.

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
costs almost nothing to state.

This one change is most of the win. Split into planes and coded, the three-minute
arrangement falls from 11 bytes a tick to about 1.7.

### 2.2 Pitches instead of dividers

A tone channel names a pitch by the **divider** the hardware counts down from, which
takes two bytes and runs the opposite way to the note: higher notes have smaller
dividers, and the steps between them are uneven. The encoder replaces the two
divider planes with one **pitch index** — how far the note sits above the lowest
pitch the table covers — and the song block carries a table the driver resolves it
through. Every channel is then two planes, and a tick is eight bytes before any
coding at all.

Saving a byte a tick is the smaller half of why this matters. The larger half is
that **a pitch index can be transposed and a divider cannot.** The same figure played
at five pitches is five unrelated byte sequences in divider space; in index space it
is one sequence and five offsets. That is what turns a repeated sample into a single
dictionary entry in §5.

## 3. The token language

Each plane is written as a sequence of **tokens**, and the driver reads them forward,
one tick at a time. There are three things a token can say, and the opcode byte's top
two bits say which:

- **Hold** — keep the value the plane reached, for up to 64 ticks. One byte.
- **Literal** — take the next few bytes, one per tick, up to 64 of them. One byte plus
  the values.
- **Phrase** — play entry *p* of the dictionary, for up to 256 ticks, optionally with
  every value shifted. Two bytes, three if the phrase needs a full id byte or a shift,
  four if it needs both.

Literals alone can write any plane, so the codec always has an answer; holds and
phrases are what make that answer short.

Two properties of the encoding do most of the work later:

**A token's count is a duration, not a length.** A phrase token says how many *ticks*
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

## 4. Reading a plane the cheapest way

A plane usually admits many readings. A run of eight identical values can be one hold,
or two holds, or a literal, or the tail of a phrase somebody else pays for. The
readings cost different numbers of bytes, and the differences compound over a song of
thousands of ticks.

So the encoder does not pick a reading by rules of thumb; it searches for the cheapest
one. The plane becomes a graph: each tick is a node, each token that could start there
is an edge to the tick after the ones it covers, and the edge's weight is the bytes
that token takes. **The cheapest path across the plane is its encoding** — and because
the weights are bytes, the search optimises the very quantity that has to fit in the
program area.

### 4.1 The edges

From each tick, the encoder offers:

- a **hold**, where the value repeats the one before it, running as far as the repeated
  run does, capped at 64 ticks;
- a **literal**, reaching this tick from the cheapest start within the last 64 ticks;
- a **phrase**, one edge per dictionary entry the plane plays from here, covering as
  many ticks as the plane agrees with it plus however long its last value carries.

Literals need care, because every one of the 64 possible starts is a candidate and
checking them all would make the parse quadratic. A literal costs its opcode and its
bytes whatever its length, so a start that is beaten by a later one is beaten for good;
keeping the live starts in that order leaves the best of them at the front, and the
whole plane's literals are priced in one pass.

### 4.2 Why the search beats taking the longest match

The obvious alternative — at each tick take the longest phrase that matches, otherwise
hold, otherwise spell out — is wrong in a way that shows up constantly. Taking a
40-tick phrase for two bytes looks better than taking a 30-tick one, until it turns out
that stopping at 30 would have let the next 200 ticks be a single hold. Costs also
depend on the dictionary: the same phrase is two bytes with a cheap id and four with an
escaped id and a shift. The search weighs those against each other; a rule of thumb
cannot.

### 4.3 Where a song comes round

A song that repeats re-enters its streams partway through rather than at the beginning,
and the driver arrives there with nothing behind it: it points each plane at a byte the
header names and starts reading. For that to work, the loop tick has to **begin** a
token on every plane, and that token has to state its values outright rather than lean
on a value the plane reached earlier.

The parse takes this as a constraint. The loop tick is a boundary: tokens may end there
and start there, and none may span it. A hold is barred from starting there, since a
hold is precisely a token that leans on what came before. Literals and phrases both
state their own values, so either can open the loop.

## 5. The dictionary

The third token kind needs something to name. The dictionary is a table of **phrases** —
runs of values a plane plays — stored once in the song block and named by tokens
wherever they occur.

A phrase's position in the table is its id, and the ids are not equally priced: the
first 63 ride inside the opcode byte, and the rest need a byte of their own. So the
order of the table is part of the encoding, and the phrases a song leans on hardest
belong at the front.

### 5.1 The instruments seed it

A song is built by placing samples at rows, so the shapes its planes repeat are
**knowable in advance rather than discoverable**. Each sample slice offers the two
planes it writes, at the pitch and level it was reconstructed at, and every row playing
that sample becomes a token naming those entries with the shift the row asks for. No
search is involved, and this is where most of a project's compression comes from: on
the three-minute arrangement the instruments alone take it from 1.6 bytes a tick to
1.13, and transposition to 0.98.

A project can offer more phrases than the table holds. When it does, each is weighed by
what it would actually spare the song, and the ones that pay most keep their place; the
export says so in the log rather than quietly dropping whichever sample happened to be
listed last.

### 5.2 The search fills the rest

The instruments cover the notes, and leave behind everything else: rests, tails, the
transitions between rows, and the whole of a reconstruction export, where each slice is
played exactly once and nothing repeats by construction.

The search works over that residue — the spans the current parse still spells out as
literals. It gathers every run of 3 to 48 ticks that appears in them and groups them by
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
candidate, once per settling round. A parse asks the same question at every tick — what
does this phrase play here, and for how many ticks — and the answer depends only on the
plane and the phrase. It cannot change between parses.

So it is measured once per plane per phrase and kept for the whole encoding. A search
round that adds one phrase measures that one phrase; everything already in the table
answers from the reading taken when it arrived. This turns the cost of an encode from
*parses × dictionary* into *dictionary*, and it is the largest reason a three-minute
song encodes in about two seconds. Phrases are also offered only at the ticks whose
first two steps match their own, so a reading covers the handful of places a phrase
could begin rather than every tick of the song.

## 6. What it achieves

Measured over a three-minute arrangement, 10800 ticks, each layer added to the ones
above it:

| what is stored | bytes per tick | ratio | ticks that fit |
|---|---|---|---|
| a record per tick per channel | 11.000 | 1.00 | 2925 |
| planes, coded | 1.735 | 6.34 | 18544 |
| planes with a pitch index | 1.598 | 6.88 | 20255 |
| phrases from the instruments | 1.126 | 9.77 | 28994 |
| phrases played transposed | 0.976 | 11.27 | 33567 |
| phrases from the search as well | **0.811** | **13.56** | **40673** |

The whole song is 8761 bytes of the roughly 32000 available, and **40673 ticks is 11.3
minutes at 60 Hz**, against the 49 seconds a record per tick reaches. Encoding it costs
about two seconds; decoding it costs the console around twenty instructions per plane
per tick, comfortably inside a video frame.

`make compression-report` writes this table over a corpus of songs, and the format's
constants are settled from it. Two of them were settled against expectation: splitting
the duty cycle out of the control byte into a plane of its own **costs** 14 %, because
volume and duty turn over together and a split pays two opcodes for what one covers;
and the pitch index earns its place twice, 8 % directly and a further 13 % through the
transposition it makes possible.

## 7. Limitations

- **The search struggles on dense reconstructions.** A reconstruction whose planes turn
  over at nearly every tick offers enormous numbers of candidates, and past a cap the
  search stops gathering and earns nothing for that song. It bites at lengths where the
  song already exceeds the program area, so it costs a diagnosis rather than a song, but
  a dense export of two minutes is stored materially larger than the same song at one.
- **The dictionary holds 255 phrases.** A project of roughly 30 to 60 samples fills it
  from its instruments alone, at which point the search has no room left to work in and
  further samples compete for slots on measured value.
- **A phrase holds at most 255 values and a token covers at most 256 ticks.** Longer
  figures are stated as several tokens, which costs a couple of bytes each time.
- **Compression is per plane.** Two channels playing the same figure at once share
  dictionary entries, and nothing exploits the correlation between a channel's own
  control and value planes.

## Appendix — the shape of the format

| quantity | value |
|---|---|
| planes | 8 — control and value, for each of four channels |
| bytes per tick before coding | 8 |
| ticks one hold covers | 1 to 64 |
| values one literal carries | 1 to 64 |
| ticks one phrase token covers | 1 to 256 |
| phrase ids inside the opcode | 63 |
| phrases in the dictionary | up to 255 |
| values in a phrase | up to 255 |
| candidate lengths the search gathers | 3 to 48 |
| decoder state on the console | 64 bytes of zero page, 8 per plane |

Where things live:

| concern | module |
|---|---|
| planes, and the pitch index | `sampletones_player.compression.planes`, `.pitch` |
| the token kinds and their byte costs | `sampletones_player.compression.tokens` |
| the cheapest reading of a plane | `sampletones_player.compression.parse` |
| the dictionary, its entries and its pruning | `sampletones_player.compression.dictionary` |
| phrases the instruments offer | `sampletones_player.compression.seeds` |
| phrases the search earns | `sampletones_player.compression.search` |
| what a phrase plays against a plane | `sampletones_player.compression.matches` |
| encoding, and the decoder the driver is held to | `sampletones_player.compression.encode`, `.decode` |
| the opcode layout and its bounds | `sampletones_player.specification.compression` |
