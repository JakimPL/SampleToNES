# Bugs and to-dos

This is the working ledger of what is still owed: to-dos, deviations from the architecture, and known
bugs. Read it before starting work in an area. Add an entry when a change knowingly leaves something
behind. Each entry says what is owed and why, and the code and the change that closes it hold the rest.

## To-dos

### Navigation

* Interface scale
* Keyboard navigation of the trees, and of the converter's list of gathered recordings: a cursor the arrow
  keys move, `Home` and `End`, and folders opened and closed from the keyboard.
* Waveform LOD for zooming
* Drag and drop of browser nodes onto views, such as a reconstruction onto Samples.
* Tabs for several reconstructions in the Reconstruction view.
* Application installation progress bar

### Tracker

The first two entries are the settings an imported `.fti` reports as left behind (see
[FamiTracker export](../formats/famitracker.md#c-reading-an-instrument-file)). Each one closed is a
dimension the import starts carrying.

* Release points. A note-off cuts the channel today, so a release segment has nowhere to play.
* Arpeggio modes. Fixed, relative and scheme arpeggios import as absolute offsets today.
* Compatibility options for the FamiTracker export, so a module plays as the app does where FamiTracker's
  own rules differ, such as how it rounds a pulse level and where it places the longer rows of an uneven
  tempo.
* A note pasted across channel kinds is clamped: a period landing on a tonal channel reads as its lowest
  note, and a pitch landing on noise as the last period.
* Playing from a row starts every channel silent, so an instrument placed without a pitch at that row
  sounds nothing live, while a full play sounds it on the pitch the rows before left.
* A rebuilt grid starts without a selection, so following playback and the rebuild after a growing paste
  drop it. Keeping the selection across the rebuild closes it.
* The selection stays where it was after a paste and does not become the pasted footprint. It should
  become the pasted block.
* A note pasted through the clipboard text names its voice by list position, and one pasted through the
  in-app slot names it by id, so the same note can play two voices across projects. One naming scheme for
  both routes closes it.
* A drag past the edge and the followed playhead both write the scroll, so with **Follow rows** on they take
  turns each frame. One writer of the scroll at a time closes it.
* A MIDI key enters a note only where the caret stands on a pitch cell. Every subcolumn could take the key
  that fits it, such as a volume or an effect.
* Several MIDI keys played at once enter one note and the caret leaves it, so a chord writes the last key
  alone. Spreading a chord over the channels would close it.

### Workflow

* Waveform construction preview: a waveform drawn from the partial reconstruction while the converter
  reconstructs a single file.
* Picking several rows of the converter's list at once, so a group leaves or settles in one gesture.
* Selecting parts of a reconstruction's waveform to crop, trim, cut and paste them along with their
  instructions.
* Marking broken files where the browsers list them: a reconstruction that fails to load, one whose
  recordings are missing and a recording that cannot be read could stand in a warning or an error color,
  so the reader learns before trying to open or play one.

### Features

* A preview volume slider below the browsers, setting the level every preview plays at. The preview player
  hands each preview's source a level it reads per block, as the song reads the master gain.
* In-application guide/tutorial.
* Language selector.
* Reading only the bins the refinement asks for, since it transforms every bin the spectrum covers and
  uses a handful per frame.
* Keeping the recordings a stopped folder scan has found, so stopping a long walk keeps the count the reader
  watched climb.
* Calibrating the pitch refinement's change weight and window, which are chosen by hand today, with
  [the calibration](../tools/calibration.md). The weight counts divider steps, which span more cents in a
  high register than in a low one, and counting it in cents would weigh every register alike.
* A setting for the lowest frequency the analysis reads. It starts at the triangle's lowest note, which
  costs conversion time on music that stays higher. A floor an octave up plays lower music at its third
  harmonic, and a floor below the triangle's lowest note needs longer library samples.

### Technical

* A cartridge for songs over 30 KB. A board with bank switching (UNROM or MMC1) needs the driver and the
  song block to read across banks.
* Channel mute on the cartridge's controller, about 180 bytes of shell.
* Several songs on one cartridge, with a song list on the screen.
* A scrolling piano roll on the cartridge's screen. It needs a raster split and a second pattern table.
* Running the cartridge on a real console, and on Mesen beside FCEUX for an accuracy check. The video
  model under `sampletones_tools/console/rom/` leaves out the odd-frame dot skip, the sprite-zero and
  overflow flags and PAL timing.
* Renaming the program export setup's `nsf` names (`NSFExportLogic`, `ui/panels/dialogs/nsf.py`, the
  `settings.nsf` keys) now that the setup serves the cartridge as well.

* Screen scenarios on Windows and macOS. They run on Linux alone, and whether DearPyGui opens its window on
  GitHub's Windows and macOS runners is unverified.
* An upgrade path for the configuration and the session state. A file an older build left behind is read
  as the loader happens to, and no archived files of older builds test it.
* A `project.json` written at format 1.1 before a row's pitch gained its face still carries `transpose`,
  which the loader drops, since the upgrade chain is idle on an equal version. Files a release wrote are
  carried over.
* The element enums that outlived their keys. The language-keys check treats a key named through an
  element enum as the whole enum, so a key no call uses goes unnoticed. Spelling each key at its call site
  makes the check exact.
* Per-tab undo routing, so each tab undoes its own document.
* A history of its own for a standalone reconstruction document, one loaded from disk and not opened as a
  project sample. An edit to such a document is undoable nowhere ([undo](application/undo.md)), so an edit
  that silences a channel or lets a recording go is reversible only by reloading the file.
* A channel edit's history entry owns every instruction of the channel, though the edit changes a few
  frames. A rebuild makes each frame of the channel anew, so on a four-channel conversion an entry has
  about a quarter of the document. Keeping the old instruction wherever the rebuilt one equals it brings an
  entry down to the frames the edit changed ([undo](application/undo.md)).
* Improve performance of the browser's favorite scan of the entire tree per click
* The `fft` and `logfft` analysis floors. Their window spans two cycles of the pulse's lowest note, so the
  triangle's lowest octave reaches them by its harmonics alone. Covering it doubles their window and
  coarsens their timing.
* A constant-Q column holds each wavelet up to a sample off its frame's middle, by the parities of the frame,
  the wavelet and the longest wavelet: at the defaults every even-length wavelet sits half a sample early.
* A target that wavers for `test_decoding.py`, whose two-tone target wavers at no frame once the extraction
  reads its opening, so the cases holding the greedy decoder against the Viterbi one stand as expected failures.
* The joint assignment for stems that share channels. It solves each stem on its own channels, so a setup
  where two stems may take one channel is refused under `generation.assignment.method: joint`. A joint
  choice across stems, ordered by the hierarchy, closes it.
* The joint assignment's speed against the picks is measured on the calibration benchmark alone. A case in
  `tests/benchmarks/` needs the full library, which an installation builds once.
* A `contour` reading of the render where the recording falls silent. Its readings over time cover the
  recording's audible frames, so a render ringing on after a short hit reaches it through the band
  readings alone.
* The joint assignment's fits (`fitted_levels`, `fitted_combinations`) scale and add feature values, so they
  read a frame's power exactly at a transformation gamma of zero alone.
* The combinations decoder moves two channels at once only within its pool: the choice with channels
  silenced, the finalists and the choice of the frame before. The Viterbi decoder may take two column
  alternatives on two channels together, which keeps it ahead on some pieces, such as Super Mario Bros. at
  the true level.
* The combinations decoder holds a quiet pulse through a noise note. The criterion prices a pulse on a
  partial of the noise 0.05 to 0.14 per frame below the noise alone, and the pool offers one such pulse in
  every frame of the note, so the path keeps it. The per-channel decoder reads a different pulse in each
  frame's column and stays silent. Single noise notes fall from 82% to 60% right and the drum sequence from
  98% to 86%. A criterion that prices the pulse above the partial it explains closes it.
* A frame heard among its neighbors loses short drum hits. The first pass holds a quiet noise under a
  staccato bass's tail, and the pass removes it, so a hit of one to three frames stands alone: its frame
  prefers quiet low pulses beside the noise, its decay prefers silence, and the decoder's on/off toll
  outweighs what the hit saves. On Castlevania the written noise frames left silent rise from 12 to 154,
  and a toll of 0.05 brings back 24 of them. A criterion that prices the pulses above the noise they
  cover, together with a toll a hit can pay, closes it. On a recording the same choices break the noise
  and the triangle into short runs: Can't Stop as a whole mix sounds its noise in 49 runs where the
  first pass held 7, the triangle in 52 where it held 18, and its channels change from 17 to 31 times a
  second, while the readings in nats hold.
* A calibration run's fingerprint holds the version the package declares, which moves at a release, so a
  resume across source edits made between two releases takes up the records written before them.
* A listening page reads the order of a run's variants from its `run.json`, so `--board` refuses a run
  written before runs kept one. Such a run's records also read at the default level, so a run of several
  levels plays every render beside the one recording it kept, the level it wrote last.
* The calibration's MIDI reader keeps running status across meta and system-exclusive events, which the
  MIDI standard says cancel it, so a file leaving out the status byte after one reads under the status
  before it.
* The calibration's MIDI reader loses a note struck again at the tick it is released when the note on
  comes first: the strike ends the old note there, and the release then ends the new one before it sounds.

## Architecture

Where the codebase stands apart from [`architecture.md`](architecture.md). A deviation is recorded here
once review has seen it and let it stand, so this section, and not the code, is the memory of what is
currently out of line. An entry leaves when the code meets the contract again.

* The two sequencer grids implement the same machinery twice. The order and tracker panels each declare the
  same block and channel hooks, build the same `ChannelSwitch`, tint a channel the same way, and run the
  same held-pointer drag, right-click hit-test and key dispatch. The shared `ui/panels/sequencer/grid/`
  package is where these belong, and `# TODO: to abstract` markers stand at the blocks. Pylint's
  duplicate-code report names each pair.
* `application.py` and `ui/elements/tree/tree.py` each hold several concerns in one module, past the size
  at which the sequencer panels were divided into subpackages. Each divides the same way: a module per
  concern, with the class that stays holding the collaborators and the public surface.
* The tab coordinators' and the application's unit tests build their object through `__new__` and fill its
  private fields by hand, so a case describes a method and not the wired object, and a hook left unset goes
  unseen.
* Which recordings a mix is built from is decided in `ui/` until **Add** is pressed. The chooser holds the
  pick as its own set and asks the view model how a gesture moves it, so a projection computes state
  transitions. The logic layer hears only the answer. Principles 3 and 4 put that machine in `logic/`,
  with the chooser drawing what a view model says and reporting the gesture. Moving it is a phase and not
  a patch, because the dialog drives the pick today.
* Every gesture in the converter re-derives the whole setup, so its cost grows faster than linearly with
  the number of recordings. Holding the rows against the gathering that produced them, and deriving entries
  for the recordings a gesture moved, closes it.
* The automation unit reaches two private members: the regeneration hold stands in for
  `RegenerationService._run` and reports through `_emit`, and the tracker view reads the caret's box from
  `CaretOverlay._rectangle`. Each is a seam a scenario needs, which [screens](application/screens.md)
  says the application offers as a public one.
* The render thread still reads a reconstruction file and its recordings from disk, at an opening and
  when a browser tree plays one, and renders the instrument the plot card draws and the sequencer's
  instrument preview; every other sound the interface draws or plays, the original line included, is a worker's
  result ([the render thread](application/render-thread.md)).
* PortMidi notices an unplugged keyboard only at its next listing, so on Windows and macOS the status bar
  tells it when the reader opens the MIDI settings or presses **Refresh**. Linux's ALSA backend tells it at
  once. Windows' own timing is unmeasured.
* PortMidi reads its device list once, so a keyboard plugged in after the application started appears
  after a restart on Windows and macOS.

## Bugs

* `tests/screens/reconstructions/instruments/test_note_keys.py` reads whether a key sounded within a fixed
  count of frames, so on a loaded machine a key's sound lands after the count and the case fails, at any of
  its steps. Waiting on the sound itself, with a time limit, closes it.
* A library file with an upper-case extension (`….INS`) on a file system that tells cases apart is listed
  by the Main tab's explorer, which offers to load it, while the Instructions tab's library card passes it
  by and the load reports the library missing. A library key names its file as `….ins`, so carrying the
  name on disk through the catalog closes it.
* A reconstruction or project stored with a range of notes beyond 24–119 refuses to load, since the range
  joined a library's identity and is held to the notes instructions name. Such a range takes a hand-edited
  configuration that reused a library built for another range. Clamping a stored range into 24–119 as a
  document loads closes it.
* A reconstruction's folder name hashes the library and generation settings, and leaves out the range of
  notes. Converting one recording under two ranges therefore uses two libraries and writes both results
  into one folder under one name. Adding the range to `ConfigDirectoryFields.settings_hash` closes it, and
  renames the folders an earlier build made.
* A screen scenario that ends within the first frames after the application starts never stops it. Its
  Exit leaves the application drawing, and the run waits until the suite's timeout, which ends the parent
  process and leaves the scenario's own process running at several cores. A scenario whose body is a single
  check that holds at startup reproduces it.
* A click on the History card's line in force takes its highlight off. The jump goes nowhere, so the card
  repaints nothing and shows no line in force until the next step.
* A rate change's retune can land as an entry of its own. When another gesture commits before the
  samples' background retune lands, the retuned samples record a second entry, so undoing it leaves the
  project at the new rate over samples tuned for the old one.
* A silent triangle renders the middle of its wave, where the console holds the step it stopped on. A
  faithful hold needs a DC-blocking output stage at every mix (the reconstruction's render, the sequencer
  and the song render), since nothing drains a held level today.
* The spectral weights read each bin at its upper edge, half a bin above its center, under every spectrum
  method (`calculate_weights_from_edges`).
* The Viterbi decoder holds the quietest noise through a steady constant-Q tone whose first two and last two
  frames ask for it, since the path holding it costs less than one stopping and starting it
  (`test_frame_objective.py`).
* Another voice inside a harmonic's bin pulls the pitch reading. A partial of another voice within half a
  semitone of one of a note's harmonics shares that harmonic's bin and adds to its reading: a 65 Hz bass
  under a steady 330 Hz pulse reads about 4 cents off, and within a cent alone.
* The Sample column shows no sample on a frame's first rows, since its reading starts over at each frame. It
  offers no transpose or volume there, while playback applies them to the sample the previous frame left
  sounding. The rows the tracker shows beside a frame read the same way, each from its own frame's start.
