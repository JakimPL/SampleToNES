# Configuration

_SampleToNES_ reconstructs according to a **generation configuration** — the
sample rate, the NES frequency, how the audio is analyzed, and how candidates are
scored. The settings you reach for most often are on the **Main** tab; the rest
live in the configuration file, for when you want to go deeper.

Which channels a recording may use is not one of them. The NES has four sound
channels — **Pulse 1**, **Pulse 2**, **Triangle**, and **Noise** — and you pick
which of them each recording takes in the converter's list, every time you set up
a conversion. See [choosing which channels a recording
uses](interface.md#choosing-which-channels-a-recording-uses).

## From the interface

Three cards on the **Main** tab hold the everyday settings:

- **General settings** — **Normalize audio** and **Quantize audio**, and the
  **Sample rate** and **NES frequency** a library is built for.
- **Source settings** — the **Drive** a run is pushed with, and the channels and
  bends of the recording you picked out of the converter's list.
- **Advanced settings** — the **Method** and **Feature scaling**, which set how
  the audio's frequency content is measured and weighted (see [Reconstruction
  algorithms](../concepts/reconstruction.md)); the **Workers** count; and the
  instruction library and output folders. **View ▸ Show advanced settings**
  reveals this card.

Changing any of these updates your configuration, which is saved to `config.json`
(see [Where your files live](files.md)).

## In the configuration file

The configuration holds more than the interface shows. The finer controls — the
[selector](../concepts/reconstruction.md) (greedy or Viterbi), the phase aligner,
the scoring weights and distance metric, the number of candidates kept per frame,
and so on — can be edited directly in `config.json`. The
[configuration file reference](../formats/configuration.md) lists every section
and key, and [Reconstruction algorithms](../concepts/reconstruction.md) explains
what they do and lists the defaults.

You can also load and save whole configurations from the **Reconstruction** menu
(**Load generation settings...** and **Save generation settings...**), or point the
app at one on the [command line](command-line.md) with `--config`.

## Deployment settings

A couple of settings — the log level and strict history checking — are decided when
the application is packaged, not by you, so they are not part of your
configuration. They exist for development and support.
