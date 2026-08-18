# SampleToNES

## v0.3.1 [2026-07-31]

* Added support to [Bitphase](https://github.com/paator/bitphase).
* Fixed arpeggio editing shifting a sample's pitch permanently.
* Enhanced application options:
    * Display settings
    * Theme selector
    * Keybinding settings
* Bumped the reconstruction data-version to `2.1`.
* Improved Sequencer module playback.
* Added song export to WAV/MP3.
* Added tracker selection operations.
* Added a _SampleToNES_ logo.

## v0.3.0 [2026-07-31]

* Added a _Sequencer_ view with FamiTracker-style patterns.
* Added project export in a FamiTracker-compatible format.
* Improved matching algorithms and extended available methods (`LogFFT`, `CQT`).
* Improved the general layout of the application.
* Changed the internal file formats (`.stn`, `.ins`).
* Switched to `uv` as the package manager.
* Detect the NVIDIA driver at setup and install the matching _CuPy_ build automatically, on Linux and Windows.

## v0.2.3 [2026-01-09]

* Improved the application's graphical interface.
* Added the main page with filesystem explorer.
* Added editing and saving reconstructions.
* Added audio settings panel.
* Implemented instructions library autogeneration.
* Simplified instructions library tree.

## v0.2.2 [2025-11-21]

* Added GPU support via _CuPy_.
* Fixed generation bugs.
* Made minor visual improvements.
* Improved code quality.
* Released the application.

## v0.2.1 [2025-11-17]

* Optimized the output file structure.
* Improved application error handling.
* Enhanced task processing communication with the GUI.
* Fixed installer bugs.
* Created a Python package and an application installer via _PyInstaller_.

## v0.2.0 [2025-11-08]

* Created a graphical interface for the application.
* Added application content:
    * Instruction instruction data explorer
    * Audio reconstruction viewer
* Included instruction data creation and converter windows.
* Added audio graphs and spectrum plots.
* Implemented audio playback.

## v0.1.0 [2025-10-23]

* Added spectral features and FFT windows for the sample approximator.
* Included mixer levels for adjusting the general amplitude of sound.
* Created an instruction instruction data for reconstruction optimization.
* Added instruction data and generation configurations.

## v0.0.1 [2025-09-24]

First version of _SampleToNES_, containing basic reconstruction scripts and all 2A03 generators.
