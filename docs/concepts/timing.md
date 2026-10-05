# Song timing

This document explains how a song's tempo becomes the whole number of ticks each row lasts. Read it before
changing the groove, or when you need to know why the rows of a song last unequal ticks. You can read it
without the source code, which lives in `sampletones_core/timing/`.

## 1. The problem

A tracker plays a song row by row, and every row lasts a whole number of [ticks](../glossary.md#tick). The
project's settings ask for an exact row length:

```
ticks_per_row = speed × nes_frequency × 150 / (tempo × 60)
```

At tempo 150 and 60 Hz this is the speed itself. At most other tempi it falls between two whole numbers.
At 60 Hz, speed 6 and tempo 125, a row should last 7.2 ticks. A row can last 7 ticks or 8, so the song
mixes the two, and the mix decides how the rhythm feels. The ticks each row lasts are the song's
[groove](../glossary.md#groove).

The [meter](../glossary.md#metric-highlight) groups the rows. The first highlight is the beat and the
second is the bar. The defaults, 4 and 16, give bars of four beats of four rows. The tempo counts beats.

## 2. What a good groove does

Four properties describe a good groove.

1. **It keeps time.** Every bar starts on the tick nearest the moment the tempo puts it at. The rounding
   never adds up, so the song holds its tempo however long it plays.
2. **It keeps proportion.** Every row lasts the whole number just below or just above its exact length:
   7 or 8 ticks for 7.2.
3. **It keeps accents.** The longer rows go to the strongest positions. In a bar, the first half of the
   beats comes first, then the first of each half, and so on down. In a beat, the first row comes first,
   then the middle row, then the quarters. At 7.2 ticks a row, a bar of four beats plays:

   ```
   8 7 7 7 | 8 7 7 7 | 8 7 7 7 | 7 7 7 7      115 ticks, against an exact 115.2
   ```

4. **It needs no look-ahead.** A player knows how long a row lasts when it reaches it, without reading the
   rows after it.

**The four can conflict.** Suppose the speed could change in the middle of a beat. A player without
look-ahead would then have to decide the length of a beat's first row before knowing whether the beat
earns a surplus tick, which property 3 wants on that row. No procedure keeps all four in that case, while
any three of them can be kept together. A _SampleToNES_ song has one speed throughout, so its groove keeps
all four.

**Time is kept at the bar line.** Starting every beat on its nearest tick, too, would put the surplus
wherever the running count happens to land, which breaks property 3. So the bar lines stay exact, and a
beat inside a bar leans toward its strong positions. In common time a beat starts within about a tick of
its exact moment. A bar holding many beats is halved more times, so its beats can stray further: up to
about three ticks in a bar of 256 one-row beats, the deepest the settings allow.

## 3. How the ticks are placed

**The rate is held within what the engine plays.** A row lasts at least one tick. A tempo above
`2.5 × speed × nes_frequency` asks for shorter rows, so every row lasts one tick and the song plays slower
than its tempo states. FamiTracker and Bitphase play such a tempo the same way.

**Each bar takes the ticks between its own start and the next bar's start.** Each start is rounded to its
nearest tick, counted from the song's first row. This is what keeps time: no bar line is more than half
a tick away from its exact moment, however far into the song it falls.

**Two frames of one pattern can differ by a tick.** At 60 Hz, speed 6 and tempo 210, a 16-row pattern
lasts 68 4/7 ticks. The first frame plays 69 and the second 68, as the bar lines fall:

```
5 4 5 4 5 4 4 4 5 4 4 4 5 4 4 4      69 ticks
5 4 4 4 5 4 4 4 5 4 4 4 5 4 4 4      68 ticks
```

Once the exact lengths of a run of patterns add up to whole ticks, the grooves start over: here every
seven patterns, which last 480 ticks. A pass through the whole song lasts the whole number of ticks
nearest its exact length, and a song that repeats replays that pass.

**A bar's ticks are halved down to its rows.** The bar's beats are cut in two, the larger part first, so
three beats part as two and one. Each part takes the share of the ticks nearest its exact length, held to
what its rows can carry, so every row keeps proportion. Each part is halved again, and a single beat is
cut between its rows the same way. The surplus therefore settles on the strongest positions. Three rows
sharing 23 ticks, for example, play `8 7 8`.

**The meter restarts at every pattern,** as a tracker's highlights do. A pattern that isn't a whole number
of bars ends on a shorter bar. A beat of 3 rows in a bar of 7, over a 16-row pattern, gives bars of 7, 7
and 2 rows, with beats of 3, 3 and 1 in the first two.

**Every player reads the same timing.** In-app playback, rendering, the NSF export, the Bitphase export
and the tracker playback check all ask how long a row lasts by the row's place in the song. Each answer
follows from that place alone, so a player starting from any row reads its length directly.

## 4. Ticks and the clocks they play on

Rows are planned in engine ticks, at the song's NES frequency. An instrument's envelope moves once a tick,
and a note starts on a tick, so the tick is the unit a row's length can be counted in. Each way of
playing the song then turns ticks into its own time once:

- **In-app playback and rendering** turn each tick into audio samples. A tick rarely lasts a whole number
  of samples, so the samples are spread the way the ticks are spread over rows: the fraction carries from
  tick to tick.
- **The NSF** runs on the console's own call, about 60.1 times a second on NTSC. Its driver adds the song's
  rate, measured in calls, to a counter on every call and plays the ticks that fall out. A 30 Hz song
  moves on every other call, a 41 Hz song holds about one call in three, and a 300 Hz song moves up to
  five ticks a call. Any rate the settings allow therefore plays at its own speed.

Each clock carries its own remainder, so neither adds up over a song. A bar line the console plays lands
within half a tick of its exact moment plus one call. Planning the rows in ticks also keeps the NSF on the
rhythm the app plays, and its stream holds only engine ticks, so a phrase repeats wherever it is played.

## 5. The exports

**The NSF plays the app's ticks.** Its stream holds the ticks the song walk plays, and its driver re-clocks
them onto the console's call (section 4). The stream stores how long each row's phrase lasts beside the
phrase, so a frame whose groove differs from the one before costs a few more bytes than a frame that
repeats it.

**Bitphase plays the app's rows.** Its song has a speed and a tempo. At tempo 0 the speed alone sets each
row, so the export writes tempo 0 and a speed effect on every row that lasts differently from the row
before it. [Tempo as a
groove](../formats/bitphase.md#d-tempo-as-a-groove) has the details.

**FamiTracker places the longer rows by its own count.** The export writes the project's speed and tempo
as they stand, and FamiTracker carries the rounding from row to row as it plays. Its song keeps the tempo
over time, and the longer rows fall wherever its running count lands. A module's rows can therefore last
a tick more or less than the app's, while every bar stays close to where the tempo puts it. A NES
frequency other than 50 or 60 Hz reaches FamiTracker as its engine speed.

## 6. How it is checked

The test suite holds the groove of every combination of tempo, speed, NES frequency and meter it sweeps
to the properties above, across many frames of a song. It measures how far each bar line lands from its
exact moment, checks that every row lasts the floor or the ceiling of its exact length, and checks which
rows of a beat and which beats of a bar carry the surplus. It also follows the bar lines through the
console's call at several rates, and holds what a player spends asking for a row's length to a small
share of what walking the song costs.
