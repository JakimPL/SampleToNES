## To-dos

### Features

* Delete library/reconstruction (with confirmation)
* In-application theme selector (theme and palette management)
* Application tutorial (guide shown at first startup)

### Navigation

* Interface scale
* Tree navigation using keys
* Waveform LOD for zooming
* Keybindings options

### Tracker

* Basic shapes as instruments
* Selection operations on patterns and orders

### Workflow

* Waveform construction preview for single-file conversion
* Selection and trimming for a reconstruction (reconstruction editing)

### Technical

* API documentation
* Code documentation (docstrings)
* Backward compatibility: library/reconstruction upgrade scheme
* Respecting FamiTracker limitations
* Per-tab undo routing
* View-model display text via `LanguageManager` (principle 8): the project-properties timestamp (`view_model/shared/project_properties.py`) and the sequencer-grid cell string (`view_model/sequencer/grid.py`) are still hardcoded formats. Resolve the template in the panel and pass it into the projection, as the audio-settings dialog now does for its device/sample-rate/decibel labels.

## Bugs

* No refreshing after library generation
