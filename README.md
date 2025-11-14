# SampleToNES v0.2.0

## Overview

_SampleToNES_ (`sampletones`) is a WAV converter that transforms audio signals to 2A03 NES music chip basic oscillators instructions:
* 2x pulse
* triangle
* noise

without using any DPCM samples.

_SampleToNES_ allows exporting reconstructed audio files as [_FamiTracker_](http://famitracker.com/) `.fti` instruments

It supports also:

* wide range of NES frequencies, from 15 Hz to 600 Hz, including two most common standards:
    * NTSC (60 Hz)
    * PAL (50 Hz)
* various sample rates, from 8000 Hz to 192,000 Hz
* reconstruction limited to only selected oscillator:
    * `pulse1`
    * `pulse2`
    * `triangle`
    * `noise`

## Installation

### Requirements
- Python 3.12 (https://www.python.org/downloads/)
- Windows, macOS, or Linux

### Windows
1. Make sure Python 3.12 is installed and available as `python` in your PATH.
2. Double-click `install.bat` in this folder. It will build a standalone `sampletones.exe` in the same directory.
3. Run `sampletones.exe` to start the application.

### macOS / Linux
1. Make sure Python 3.12 is installed and available as `python3` in your PATH.
2. Open a terminal in this folder and run:
	```sh
	./install.sh
	```
	This will build a standalone `sampletones` executable in the same directory.
3. Run `./sampletones` to start the application.

### Alternative: Install as a Python Package

If you already have a Python 3.12 environment set up (for example, using `venv` or another virtual environment tool), you can install and run _SampleToNES_ directly as a package:

1. Open a terminal in this folder.
2. Activate your Python 3.12 environment.
3. Install the package:
    ```sh
    pip install .
    ```
4. Run the application:
    ```sh
    sampletones
    ```


## Workflow

### Libraries

To optimize sample reconstruction, all single oscillator instruction are precalculated within their waveforms and spectral information.

The library depends on the following configuration properties:
* `change_rate` (frequency, usually NTSC or PAL)
* `sample_rate` (in Hz)
* `transformation_gamma`, which determines the transformation of the spectral information:
    * `0` - raw absolute values of Fourier Transform
    * `100` - absolute values transformed via $\log\left(1 + x\right)$ operation
    Intermediate values interpolate between these two.

Each set of parameters correspond to a different library. Libraries are generated using library generator present in the application.

Libraries are stored as `.dat` files in the user documents folder, e.g.:
```
sr_44100_fl_1470_ws_1615_tg_0_ch_3dffb3e16110e06d75730c1e14053371.dat
```


## Application files

All local files, that is:
* configuration (`config.json`)
* libraries (`.dat`)
* reconstructions (`.json`)

are stored in the default application directory. The path depends on the operating system.

### Windows

The default path of the library is:
```
C:\Users\<user>\AppData\Local\Stage Magician\SampleToNES\library
```

### Linux

Local files can be found in the following directory:
```
/home/<user>/.local/share/SampleToNES/library
```

## Reconstructions