## To-dos

### Navigation

* Interface scale
* Tree navigation using keys
* Waveform LOD for zooming
* Alt for scrolling graphs
* Drag and drop
* Multiple Reconstruction views
* In-project sample selection in Reconstruction view
* Playing a fragment by clicking on a waveform
* Application installation progress bar

### Tracker

* Pitch and hi-pitch envelopes: a per-tick period bend, where an instruction's pitch is a whole
  semitone. Sounding them needs a sub-semitone offset in the instruction model and raw timer values
  in the NSF planes, which reaches the reconstruction search space, the instruction library and the
  compression pitch table. The two sequences reach a tracker file today and are written empty.
* Release points: `NoteValue.RELEASE` stands in the FamiTracker specification while a note-off cuts
  the channel. A release segment would need the playback walk, the NSF driver and `NoteOff` to gain
  one.
* Arpeggio modes: a sequence's `setting` byte states absolute. Fixed, relative and scheme need an
  enum of their own, and scheme needs the item bit-packing FamiTracker gives it.
* A loop point per envelope: a voice states one point, applied to every populated sequence.
* A sample's loop point is offered as a switch in the voice list, though the model carries the
  point for both kinds of voice.
* Exporting a shape as an instrument file from the Reconstructions tab.

### Workflow

* Waveform construction preview for single-file conversion
* Selection operations on a reconstruction
* Reconstruction trimming

### Features

* In-application guide/tutorial
* Language selector

### Technical

* API documentation
* Code documentation
* Backward compatibility: library/reconstruction upgrade scheme
* Respecting FamiTracker limitations
* Per-tab undo routing
* In-application console
* Improve performance of browser favorite scan of the entire tree per click

## Bugs

* No refreshing after library generation
* Misaligned dialog boxes sizes at initialization
* Audible noise instructions when matching near-silent samples for FFT γ0
